# Discord bot configuration

Discord는 분석 결과 전송 채널로 사용할 수 있습니다. 단순 전송만 필요하면 Webhook 방식을 사용하고, Bot API로 메시지를 보내야 하면 Bot Token과 Channel ID를 사용합니다.

## Configuration modes

| Mode | Required values | Use case |
| --- | --- | --- |
| Webhook | `DISCORD_WEBHOOK_URL` | 설정이 가장 단순한 결과 전송 |
| Bot API | `DISCORD_BOT_TOKEN`, `DISCORD_MAIN_CHANNEL_ID` | 봇 계정으로 채널에 메시지 전송 |

Webhook URL이 설정되어 있으면 Discord 전송기는 Webhook을 우선 사용합니다.

## Create a Discord application

1. Open [Discord Developer Portal](https://discord.com/developers/applications).
2. Create an application.
3. Open the `Bot` section and create a bot user.
4. Reset and store the bot token as `DISCORD_BOT_TOKEN`.
5. In `OAuth2` > `URL Generator`, select `bot` and `applications.commands`.
6. Grant the bot permissions to send messages, embed links, attach files, read message history, and use slash commands.
7. Open the generated invite URL and add the bot to the target server.

## Find the channel ID

1. In Discord, enable developer mode.
2. Right-click the target channel.
3. Copy the channel ID and set it as `DISCORD_MAIN_CHANNEL_ID`.

## Environment variables

Webhook mode:

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your_webhook_id/your_webhook_token
DISCORD_MAX_WORDS=2000
```

Bot API mode:

```env
DISCORD_BOT_TOKEN=your-discord-bot-token
DISCORD_MAIN_CHANNEL_ID=123456789012345678
DISCORD_MAX_WORDS=2000
DISCORD_BOT_STATUS=Stock analysis | /help
```

## Command examples

Discord command handling uses the same command names as the common bot dispatcher.

```text
/help
/status
/market
/analyze 005930
/analyze AAPL full
```

KR stock codes use six digits. US symbols use uppercase ticker symbols such as `AAPL` or `MSFT`.

## Verification

1. Set either Webhook mode or Bot API mode values in `.env`.
2. Restart the service so configuration is reloaded.
3. Send `/help` to confirm the bot command surface.
4. Send `/analyze 005930` or `/analyze AAPL` to confirm analysis submission.
5. Check application logs if Discord accepts the request but no message appears in the channel.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| No message is sent | Confirm `DISCORD_WEBHOOK_URL` or `DISCORD_BOT_TOKEN` + `DISCORD_MAIN_CHANNEL_ID` is set. |
| Bot API message is rejected | Confirm the bot is installed in the server and can send messages in the target channel. |
| Messages are truncated | Lower `DISCORD_MAX_WORDS` or use a channel that can receive longer chunks. |
| Slash commands do not appear | Wait for Discord command sync or reinstall the bot with `applications.commands`. |

Keep tokens out of source control. Use `.env`, repository secrets, or deployment platform secrets.
