import unittest
from unittest.mock import Mock, patch

from samuel.commands import CommandHandler
from samuel.brain import AIBrain, ProposedAction


class CommandTests(unittest.TestCase):
    def test_nvm_cancels_pending_question(self):
        speak = Mock()
        handler = CommandHandler(speak)
        handler.pending = ("confirm_search", "old query")
        handler.handle("nvm")
        self.assertIsNone(handler.pending)
        speak.assert_called_once_with("Cancelled.")

    def test_point_target_removes_on_my_screen_suffix(self):
        point = Mock()
        CommandHandler(Mock(), point_to=point).handle("point at SAMUEL on my scrren")
        point.assert_called_once_with("samuel")

    def test_close_window_requires_confirmation_then_executes(self):
        closer = Mock()
        handler = CommandHandler(Mock(), close_window=closer)
        handler.handle("close this window now")
        self.assertEqual(handler.pending, ("confirm_close_window", "active"))
        closer.assert_not_called()
        handler.handle("yes")
        closer.assert_called_once_with()

    def test_chatgpt_compound_message_requires_confirmation(self):
        message_app = Mock()
        handler = CommandHandler(Mock(), message_app=message_app)
        handler.handle("open chat gpt app and send it a message saying Hi")
        self.assertEqual(handler.pending, ("confirm_message_app", "chatgpt|Hi"))
        message_app.assert_not_called()
        handler.handle("yes do it now")
        message_app.assert_called_once_with("chatgpt", "Hi")

    def test_new_open_command_replaces_stale_search_confirmation(self):
        handler = CommandHandler(Mock())
        handler.pending = ("confirm_search", "kali folder on screen")
        handler.handle("open chat gpt")
        self.assertEqual(handler.pending, ("app_or_website", "chatgpt"))

    def test_open_folder_on_screen_without_possessive(self):
        handler = CommandHandler(Mock(), open_visual=Mock())
        handler.handle("open kali folder on screen")
        self.assertEqual(handler.pending, ("confirm_visual_open", "kali folder"))

    def test_analyze_screen_calls_host_capture(self):
        analyze = Mock()
        handler = CommandHandler(Mock(), analyze_screen=analyze)
        handler.handle("analysis my scrren")
        analyze.assert_called_once_with("analysis my scrren")

    def test_capture_typo_calls_host_capture(self):
        analyze = Mock()
        handler = CommandHandler(Mock(), analyze_screen=analyze)
        handler.handle("capturm and tell me ehat you see")
        analyze.assert_called_once_with("capturm and tell me ehat you see")

    def test_what_am_i_doing_calls_host_capture(self):
        analyze = Mock()
        handler = CommandHandler(Mock(), analyze_screen=analyze)
        handler.handle("what i am doing edxplaine it")
        analyze.assert_called_once_with("what i am doing edxplaine it")

    def test_reported_extra_typo_screen_request(self):
        analyze = Mock()
        handler = CommandHandler(Mock(), analyze_screen=analyze)
        handler.handle("what ia am doing edxplaine it")
        analyze.assert_called_once_with("what ia am doing edxplaine it")

    def test_describe_screen_response_is_parsed(self):
        brain = AIBrain()
        brain.enabled, brain.api_key = True, "sk-test"
        response = {"output": [{"type": "function_call", "name": "report_screen_summary",
                    "arguments": '{"summary":"You are editing Python in VS Code."}'}]}
        with patch.object(brain, "_post_responses", return_value=response):
            result = brain.describe_screen(b"image", "what am I doing", 800, 600)
        self.assertEqual(result, "You are editing Python in VS Code.")

    def test_open_folder_on_screen_requires_confirmation_then_executes(self):
        speak, visual_open = Mock(), Mock()
        handler = CommandHandler(speak, open_visual=visual_open)
        handler.handle("open the kali folder on my screen")
        self.assertEqual(handler.pending, ("confirm_visual_open", "kali folder"))
        visual_open.assert_not_called()
        handler.handle("yes do it now")
        visual_open.assert_called_once_with("kali folder")
        self.assertIsNone(handler.pending)

    def test_visual_open_can_be_cancelled(self):
        visual_open = Mock()
        handler = CommandHandler(Mock(), open_visual=visual_open)
        handler.handle("open the kali folder on my screen")
        handler.handle("no")
        visual_open.assert_not_called()
        self.assertIsNone(handler.pending)

    def test_visual_open_debug_mode_explains_limitation(self):
        speak = Mock()
        CommandHandler(speak).handle("open the kali folder on my screen")
        self.assertIn("desktop app", speak.call_args.args[0])

    def test_double_click_phrase_uses_visual_open(self):
        handler = CommandHandler(Mock(), open_visual=Mock())
        handler.handle("double click the kali folder")
        self.assertEqual(handler.pending, ("confirm_visual_open", "kali folder"))

    def test_open_google_chrome_is_not_a_search(self):
        handler = CommandHandler(Mock())
        with patch.object(handler, "_open_windows_app") as opener:
            handler.handle("open Google Chrome")
            opener.assert_called_once_with("chrome")

    def test_follow_up_remembers_confirmed_search(self):
        handler = CommandHandler(Mock())
        handler.handle("open something unknown")
        self.assertEqual(handler.pending, ("confirm_search", "something unknown"))
        with patch.object(handler, "_search") as search:
            handler.handle("okay open")
            search.assert_called_once_with("something unknown")
            self.assertIsNone(handler.pending)

    def test_app_or_website_follow_up(self):
        handler = CommandHandler(Mock())
        handler.handle("go to Facebook")
        self.assertEqual(handler.pending, ("app_or_website", "facebook"))
        with patch.object(handler, "_open_website") as opener:
            handler.handle("website")
            opener.assert_called_once_with("facebook")

    def test_point_to_uses_screen_callback(self):
        callback = Mock()
        handler = CommandHandler(Mock(), callback)
        handler.handle("point to recycle bin")
        callback.assert_called_once_with("recycle bin")

    def test_point_at_uses_screen_callback(self):
        callback = Mock()
        handler = CommandHandler(Mock(), callback)
        handler.handle("point at chat gpt icon")
        callback.assert_called_once_with("chat gpt icon")

    def test_point_in_debug_mode_is_not_silent(self):
        speak = Mock()
        handler = CommandHandler(speak)
        handler.handle("point at chat gpt icon")
        self.assertIn("debug console", speak.call_args.args[0])
        self.assertIn("start_samuel.bat", speak.call_args.args[0])

    def test_ai_action_requires_confirmation(self):
        brain = Mock(enabled=True)
        brain.plan.return_value = ProposedAction("search", "Python decorators", "I will search for it.")
        handler = CommandHandler(Mock(), brain=brain)
        handler.handle("find me a lesson about decorators")
        self.assertEqual(handler.pending, ("confirm_ai_action", "search|Python decorators"))
        with patch.object(handler, "_search") as search:
            handler.handle("yes")
            search.assert_called_once_with("Python decorators")

    def test_missing_key_requests_setup(self):
        callback = Mock()
        brain = Mock(enabled=False)
        handler = CommandHandler(Mock(), brain=brain, need_ai=callback)
        handler.handle("organize this complicated task for me")
        callback.assert_called_once_with()

    def test_vision_location_is_parsed_without_clicking(self):
        brain = AIBrain()
        brain.enabled = True
        brain.api_key = "sk-test"
        response = {"output": [{"type": "function_call", "name": "report_location", "arguments":
                    '{"found":true,"label":"red car","x":10,"y":20,"width":100,"height":50,"confidence":0.9}'}]}
        with patch.object(brain, "_post_responses", return_value=response):
            result = brain.locate_visual(b"image", "red car", 800, 600)
        self.assertEqual(result["x"], 10)
        self.assertEqual(result["label"], "red car")

    def test_greeting_is_handled_locally(self):
        speak = Mock()
        brain = Mock(enabled=True)
        handler = CommandHandler(speak, brain=brain)
        handler.handle("hi")
        speak.assert_called_once_with("Hi! How can I help you?")
        brain.plan.assert_not_called()

    def test_internal_prompt_label_is_not_spoken(self):
        speak = Mock()
        handler = CommandHandler(speak)
        handler._propose_ai_action(ProposedAction("reply", "local conversation", ""))
        self.assertNotEqual(speak.call_args.args[0], "local conversation")

    def test_screen_privacy_question_is_local(self):
        speak = Mock()
        handler = CommandHandler(speak)
        handler.handle("can you see my screen")
        self.assertIn("only capture", speak.call_args.args[0])

    def test_typo_open_chrome(self):
        handler = CommandHandler(Mock())
        with patch.object(handler, "_open_windows_app") as opener:
            handler.handle("opne chrom")
            opener.assert_called_once_with("chrome")

    def test_typo_open_calculator(self):
        handler = CommandHandler(Mock())
        with patch.object(handler, "_open_windows_app") as opener:
            handler.handle("pleas opne calcultor!!!")
            opener.assert_called_once_with("calculator")

    def test_mixed_case_and_whitespace(self):
        handler = CommandHandler(Mock())
        with patch.object(handler, "_open_windows_app") as opener:
            handler.handle("   OpEn   GoOgLe ChRoMe   ")
            opener.assert_called_once_with("chrome")

    def test_yes_please_confirms(self):
        handler = CommandHandler(Mock())
        handler.pending = ("confirm_search", "Python")
        with patch.object(handler, "_search") as search:
            handler.handle("yes please")
            search.assert_called_once_with("Python")

    def test_yes_do_it_now_confirms(self):
        handler = CommandHandler(Mock())
        handler.pending = ("confirm_ai_action", "search|Python")
        with patch.object(handler, "_search") as search:
            handler.handle("yes do it now")
            search.assert_called_once_with("Python")

    def test_plain_chatgpt_asks_app_or_website(self):
        speak = Mock()
        handler = CommandHandler(speak)
        handler.handle("okay open chat gpt")
        self.assertEqual(handler.pending, ("app_or_website", "chatgpt"))
        self.assertIn("app or website", speak.call_args.args[0])

    def test_chatgpt_desktop_app_opens_app(self):
        handler = CommandHandler(Mock())
        with patch.object(handler, "_open_windows_app") as opener:
            handler._open("ChatGPT desktop app")
            opener.assert_called_once_with("chatgpt")

    @patch("samuel.commands.platform.system", return_value="Darwin")
    @patch("samuel.commands.subprocess.Popen")
    def test_chatgpt_opens_native_mac_app(self, popen, _system):
        handler = CommandHandler(Mock())
        handler._open_windows_app("chatgpt")
        popen.assert_called_once_with(["open", "-a", "ChatGPT"], shell=False)

    @patch("samuel.commands.platform.system", return_value="Windows")
    def test_chatgpt_opens_windows_uri(self, _system):
        handler = CommandHandler(Mock())
        with patch("samuel.commands.os.startfile", create=True) as startfile:
            handler._open_windows_app("chatgpt")
            startfile.assert_called_once_with("chatgpt:")

    def test_chatgpt_app_choice_opens_native_app(self):
        handler = CommandHandler(Mock())
        handler.handle("open chatgpt")
        with patch.object(handler, "_open_windows_app") as opener:
            handler.handle("app")
            opener.assert_called_once_with("chatgpt")

    def test_ai_point_in_debug_mode_does_not_request_fake_confirmation(self):
        speak = Mock()
        handler = CommandHandler(speak)
        handler._propose_ai_action(ProposedAction("point", "ChatGPT icon", "Point to it."))
        self.assertIsNone(handler.pending)
        self.assertIn("debug console", speak.call_args.args[0])

    def test_screen_typo_is_understood(self):
        speak = Mock()
        handler = CommandHandler(speak)
        handler.handle("can you see my scrren")
        self.assertIn("only capture", speak.call_args.args[0])

    def test_punctuation_greeting(self):
        speak = Mock()
        CommandHandler(speak).handle("Hi!!!")
        speak.assert_called_once_with("Hi! How can I help you?")

    def test_out_of_bounds_vision_box_is_clamped(self):
        brain = AIBrain()
        brain.enabled, brain.api_key = True, "sk-test"
        response = {"output": [{"type": "function_call", "name": "report_location", "arguments":
                    '{"found":true,"label":"item","x":790,"y":590,"width":500,"height":500,"confidence":0.9}'}]}
        with patch.object(brain, "_post_responses", return_value=response):
            result = brain.locate_visual(b"image", "item", 800, 600)
        self.assertEqual(result["width"], 10)
        self.assertEqual(result["height"], 10)


if __name__ == "__main__":
    unittest.main()
