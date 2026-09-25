#!/bin/bash
echo "Create an API key at https://platform.openai.com/api-keys"
read -r -s -p "Paste your OpenAI API key: " SAMUEL_KEY
echo
if [ -z "$SAMUEL_KEY" ]; then exit 1; fi
touch "$HOME/.zshrc"
if grep -q '^export OPENAI_API_KEY=' "$HOME/.zshrc"; then
  sed -i.bak 's/^export OPENAI_API_KEY=.*/export OPENAI_API_KEY="'"$SAMUEL_KEY"'"/' "$HOME/.zshrc"
else
  echo 'export OPENAI_API_KEY="'"$SAMUEL_KEY"'"' >> "$HOME/.zshrc"
fi
unset SAMUEL_KEY
echo "API key saved. Sign out/in or open a new Terminal, then restart Samuel."
