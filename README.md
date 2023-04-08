# x-ui-bot

This python code can be used to run a telegram bot specific to your server. The bot uses x-ui configurations, so you are supposed to use x-ui for it.
There's a file 'config.py'. it reads configurations from the environment, which means that, you must provide some data for this bot to run. Follow these steps:
1. create a file called '.env' next to files in this repository
2. go to telegram's botfather and get an access token, then open the .env file and do these:
```bash
export BOT_TOKEN=<your access token>
export XUI_DB_PATH=<path to x-ui db file>(optional, default to /etc/x-ui/x-ui.db)
export BOT_NAME=<your desired name for the bot>
export SSL_PUBLIC=<path to ssl public key file>
export SSL_PRIVATE=<path to ssl private key file>
export URL=<your server's domain in addition to the port, example: example.tld:port>
```
3. run ```python
  pip install -r requirements.txt```
4. run ```bash
  chmod +x clients.py && ./clients.py```
