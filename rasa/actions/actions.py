# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions

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
