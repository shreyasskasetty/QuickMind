# Create Python virtual environment with version 3.11.7
echo "Creating Python virtual environment with version 3.11.7"
python3 -m venv myenv

# Activate the virtual environment
source myenv/bin/activate

echo installing composio
pip install composio_core
pip install poetry
# Install dependencies using Poetry
echo "Running poetry install"
poetry install

poetry self add poetry-dotenv-plugin

# Login to your account
echo "Login to your Composio acount"
composio login

# Add trello tool
echo "Add google calendar and gmail tool. Finish the flow"
composio add googlecalendar
composio add gmail

echo "Enable trigger"
composio triggers enable gmail_new_gmail_message