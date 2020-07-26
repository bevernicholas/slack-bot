import os
import logging
from flask import Flask
from slack import WebClient
from slackeventsapi import SlackEventAdapter
from onboarding_tutorial import OnBoardingTutorial

app = Flask(__name__)
slack_events_adapter = SlackEventAdapter(os.environ['SLACK_SIGNING_SECRET'], "/slack/events", app)

slack_web_client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])

onboarding_tutorials_sent = {}

def start_onboarding(user_id: str, channel: str):
  onboarding_tutorial = OnBoardingTutorial(channel)
  message = onboarding_tutorial.get_message_payload()
  response = slack_web_client.chat_postMessage(**message)
  onboarding_tutorial.timestamp = response["ts"]

  if channel not in onboarding_tutorials_sent:
    onboarding_tutorials_sent[channel] = {}
  onboarding_tutorials_sent[channel][user_id] = onboarding_tutorial

@slack_events_adapter.on("team_join")
def onboarding_message(payload):
  event = payload.get('event', {})
  user_id = event.get('user', {}).get('id')

  response = slack_web_client.im_open(user_id)
  channel = response["channel"]["id"]
  start_onboarding(user_id, channel)

@slack_events_adapter.on("reaction_added")
def update_emoji(payload):
  event = payload.get('event', {})
  channel_id = event.get('item', {}).get('channel')
  user_id = event.get('user')

  if channel_id not in onboarding_tutorials_sent:
    return 
  
  onboarding_tutorial = onboarding_tutorials_sent[channel_id][user_id]
  onboarding_tutorial.reaction_task_completed = True
  message = onboarding_tutorial.get_message_payload()

  updated_message = slack_web_client.chat_update(**message)
  onboarding_tutorial.timestamp = updated_message['ts']

@slack_events_adapter.on("pin_added")
def update_pin(payload):
  event = payload.get('event', {})
  channel_id = event.get('channel_id')
  user_id = event.get('user')

  onboarding_tutorial = onboarding_tutorials_sent[channel_id][user_id]
  onboarding_tutorial.pin_task_completed = True
  message = onboarding_tutorial.get_message_payload()

  updated_message = slack_web_client.chat_update(**message)
  onboarding_tutorial.timestamp = updated_message['ts']

@slack_events_adapter.on("message")
def message(payload):
  event = payload.get('event', {})
  channel_id = event.get('channel')
  user_id = event.get('user')
  text = event.get('text')

  if text and text.lower() == 'start':
    return start_onboarding(user_id, channel_id)

if __name__ == "__main__":
  logger = logging.getLogger()
  logger.setLevel(logging.DEBUG)
  logger.addHandler(logging.StreamHandler())
  app.run(port=3000)
