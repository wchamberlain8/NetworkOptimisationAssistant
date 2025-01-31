# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions

import time
import requests

from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
#from resource_bank import TERM_DICTIONARY, COMPARISON_DICTIONARY

TERM_DICTIONARY = {
    "broadband": "Broadband is blah blah blah",
    "bandwidth": "Bandwidth is the maximum rate of data transfer across a network",
    "ethernet": "Ethernet is a wired connection that is faster and less susceptible to interference",
    "wifi" : "Wi-Fi is a wireless connection that is very convenient but can be slower and less reliable due to interference or signal loss.",
    #ADD MORE, LOTS MORE HERE
}

COMPARISON_DICTIONARY = {
    "bandwidthbroadband": "Bandwidth is the maximum rate of data transfer across a network, whereas broadband is a high-speed internet connection that is always on.",
    "ethernetwifi": "Ethernet is a wired connection that is faster and more reliable than Wi-Fi, which is a wireless connection that is more convenient but slower.",
    #ADD MORE, LOTS MORE HERE
}

class ActionHelloWorld(Action):

    def name(self) -> Text:
        return "action_hello_world"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(text="Hello World!")

        return []
    

class ActionExplainTerms(Action):
    
    def name(self) -> Text:
        return "action_explain_terms"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        term = tracker.get_slot("term")

        if term:
            explanation = TERM_DICTIONARY.get(term.lower(), "Sorry, I don't know what that is.")
            dispatcher.utter_message(text=explanation)
        else:
            dispatcher.utter_message(text="Please provide a networking term you would like explaining.")

        return []
    


    
class ActionCompareTerms(Action):
    
    def name(self) -> Text:
        return "action_compare_terms"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        term1 = tracker.get_slot("comparison_term1")
        term2 = tracker.get_slot("comparison_term2")

        if term1 and term2:
            key = "".join(sorted([term1.lower(), term2.lower()]))
            explanation = COMPARISON_DICTIONARY.get(key, "Sorry, I can't compare those two terms.")
            dispatcher.utter_message(text=explanation)
        else:
            dispatcher.utter_message(text="Please provide two networking terms you would like to be compared.")

        return []
    
#Test action that can help debug if the API is working/if Rasa can connect to it
class ActionConnectToAPI(Action):

    def name (self) -> Text:
        return "action_connect_to_api"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
       
        url = "http://127.0.0.1:8000/test"
        input_value = "test"

        try:
            response = requests.post(url, json={"input_value": input_value})
            
            if response.status_code == 200:
                response_data = response.json() 
                message = response_data.get("message", "API responded without a message.")
            else:
                message = f"Error: Received {response.status_code} from the API."

        except Exception as e:
            message = f"API call failed: {str(e)}"

        dispatcher.utter_message(text=message)

        return []

#Action to retrieve the current top consumer of bandwidth on a network 
class ActionRetrieveBandwidth(Action):

    def name (self) -> Text:
        return "action_retrieve_bandwidth"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        url = "http://127.0.0.1:8000/get_live_stats"
        startTime = time.time()

        try:
            response = requests.get(url)

            if response.status_code == 200:
                data = response.json()
                top_consumer = data.get("top_consumer")
                timeoutMessage = data.get("message")

                print(f"Top consumer: {top_consumer}")

                if top_consumer:
                    endTime = time.time()
                    elapsedTime = endTime - startTime
                    message = f"The top consumer is {top_consumer['src_mac']} using {top_consumer['total_bandwidth']:.2f} Mbps. Operation took {elapsedTime:.3f} seconds." #Added in a time record for performance checking
                elif timeoutMessage:
                    message = timeoutMessage
                else:
                    message = "No devices could be found using bandwidth."
            else:
                message = f"Error: Received {response.status_code} from the API."
        except Exception as e:
            message = f"API call failed: {str(e)}"

        dispatcher.utter_message(text=message)
        return []
    
class ActionRetrieveHistoricBandwidth(Action):

    def name (self) -> Text:
        return "action_retrieve_historic_data"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        url = "http://127.0.0.1:8000/get_historic_stats"

        try:
            response = requests.get(url)

            if response.status_code == 200:
                data = response.json()
                #extract the data

                uptime = data["uptime"]
                message = f"Network has been online for {uptime}. Here's the usage data in that time:\n"

                for device in data["stats"]:
                    src_mac = device["src_mac"]
                    byte_count = device["overall_byte_count"]
                    message = message + f"• Device {src_mac} has used {byte_count}\n"

            else:
                message = f"Error: Recieved {response.status_code} from the API"
        except Exception as e:
            message = f"API call failed: {str(e)}"

        dispatcher.utter_message(text=message)
        return []
