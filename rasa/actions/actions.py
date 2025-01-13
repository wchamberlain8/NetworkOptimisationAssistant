# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions

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

class ActionRetrieveBandwidth(Action):

    def name (self) -> Text:
        return "action_retrieve_bandwidth"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        url = "http://127.0.0.1:8000/retrieve_bandwidth"

        try:
            response = requests.get(url)

            if response.status_code == 200:
                data = response.json()
                top_consumer = data.get("top_consumer")

                if top_consumer:
                    message = f"The device using the most bandwidth is {top_consumer['src_mac']} with {top_consumer['byte_count']} bytes." #need to change this to  aactually figure out bandwith not just bytes
                else:
                    message = "No devices could be found using bandwidth."
            else:
                message = f"Error: Received {response.status_code} from the API."
        except Exception as e:
            message = f"API call failed: {str(e)}"

        dispatcher.utter_message(text=message)
        return []
