import time
import requests

from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import resource_bank

TERM_DICTIONARY = resource_bank.TERM_DICTIONARY
COMPARISON_DICTIONARY = resource_bank.COMPARISON_DICTIONARY

#Test action
class ActionHelloWorld(Action):

    def name(self) -> Text:
        return "action_hello_world"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(text="Hello World!")

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
    

#--------------------------------------------------------------------------------------------------------------------
#ActionExplainTerms - Used to return a definition of a user inputted term using the external dictionaries as a source
#--------------------------------------------------------------------------------------------------------------------
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
    

#--------------------------------------------------------------------------------------------------------------------
#ActionCompareTerms - Used to return a comparison/definitions of two user inputted terms using the external dictionaries as a source
#--------------------------------------------------------------------------------------------------------------------
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
    

#--------------------------------------------------------------------------------------------------------------------
#ActionRetrieveBandwidth - Used to return the current consumers (and top consumer) of bandwidth on the network
#--------------------------------------------------------------------------------------------------------------------
class ActionRetrieveBandwidth(Action):

    def name(self) -> Text:
        return "action_retrieve_bandwidth"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        url = "http://127.0.0.1:8000/get_live_stats"

        try:
            start_time = time.time()    
            response = requests.get(url)

            if response.status_code == 200:
                data = response.json()
                combined_data = data.get("data", {})
                print(combined_data)
                timeout_message = data.get("message")

                top_consumer = combined_data.get("top_consumer", {})
                live_flows = combined_data.get("live_flows", [])
                    
                if top_consumer or live_flows:
                    end_time = time.time()
                    elapsed_time = end_time - start_time
                    message = "🌐 Here are all the current live flows on the network: \n"
                    message += "  \n  "


                    for flow in live_flows:
                        mac, hostname = mac_translation(flow['dst_mac'])
                        if mac is None or hostname is None:
                            continue
                        bandwidth = flow.get('bandwidth', "N/A")
                        if bandwidth != "N/A":
                            bandwidth = f"{bandwidth:.2f}"
                        message += f"• Device {hostname} (MAC: {mac}) is using {bandwidth} Mbps \n"

                    if top_consumer:
                        mac, hostname = mac_translation(top_consumer['dst_mac'])
                        if mac is not None and hostname is not None:
                            top_consumer_bw = top_consumer.get('total_bandwidth', "N/A")
                            if top_consumer_bw != "N/A":
                                top_consumer_bw = f"{top_consumer_bw:.2f}"
                            
                            message += "  \n  "
                            message += f"📈 The top consumer is {hostname} (MAC: {mac}) using {top_consumer_bw} Mbps. Operation took {elapsed_time:.3f} seconds."


                elif timeout_message:
                    message = timeout_message

                else:
                    message = "No devices could be found using bandwidth."

            else:
                message = f"Error: Received {response.status_code} from the API."
        except Exception as e:
            message = f"Exception occurred in Rasa Actions: {str(e)}"

        dispatcher.utter_message(text=message)
        return []


#--------------------------------------------------------------------------------------------------------------------
#ActionRetrieveHistoricBandwidth - Used to return a list of all past devices that have used bandwidth (and how much) on the network
#--------------------------------------------------------------------------------------------------------------------
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
                message = f"🌐 Network has been online for {uptime}. Here's the usage data in that time:\n"

                for device in data["stats"]:
                    #src_mac = device["src_mac"]
                    mac, hostname = mac_translation(device["src_mac"])
                    byte_count = device["overall_byte_count"]
                    message = message + f"\t • Device {hostname} (MAC: {mac}) has used {byte_count}\n"

            else:
                message = f"Error: Recieved {response.status_code} from the API"
        except Exception as e:
            message = f"Exception occured in Rasa Actions: {str(e)}"

        dispatcher.utter_message(text=message)
        return []
    

#--------------------------------------------------------------------------------------------------------------------
#ActionThrottleDevice - Sends an input to the API to throttle a device's bandwidth
#--------------------------------------------------------------------------------------------------------------------
class ActionThrottleDevice(Action):

    def name (self) -> Text:
        return "action_throttle_device"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        url = "http://127.0.0.1:8000/throttle_device"

        try:
            device = tracker.get_slot("device")
            response = requests.post(url, json={"device": device})

            if response.status_code == 200:
                if response.json().get("message") == "success":
                    message = "Device has been throttled successfully. To stop it being throttled, simply ask me to 'Unthrottle (device name)'."
                elif response.json().get("message") == "Present":
                    message = "Device is already being throttled."
                else:
                    message = "Device could not be throttled. Please check the device name and try again. Alternatively, ask to view current devices to specify using MAC instead."
            else:
                message = f"Error: Received {response.status_code} from the API."
        except Exception as e:
            message = f"Exception occured in Rasa Actions: {str(e)}"

        dispatcher.utter_message(text=message)
        return []
    
#--------------------------------------------------------------------------------------------------------------------
#ActionPrioritiseDevice - Sends an input to the API to prioritise a device's bandwidth
#--------------------------------------------------------------------------------------------------------------------    
class ActionPrioritiseDevice(Action):

    def name (self) -> Text:
        return "action_prioritise_device"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        url = "http://127.0.0.1:8000/prioritise_device"
        
        try:
            device = tracker.get_slot("device")

            response = requests.post(url, json={"device": device})

            if response.status_code == 200:

                if response.json().get("message") == "success":
                    message = "Device has been prioritised successfully. To stop it being prioritised, simply ask me to 'Deprioritise (device name)'."
                elif response.json().get("message")  == "Present":
                    message = "Device is already being prioritised."
                else:
                    message = "Device could not be prioritised. Please check the device name and try again. Alternatively, ask to view current devices to specify using MAC instead."
            else:
                message = f"Error: Received {response.status_code} from the API."
        except Exception as e:
            message = f"Exception occured in Rasa Actions: {str(e)}"

        dispatcher.utter_message(text=message)
        return []

#--------------------------------------------------------------------------------------------------------------------
#ActionUnthrottleDevice - Sends an input to the API to unthrottle a device's bandwidth
#--------------------------------------------------------------------------------------------------------------------
class ActionUnthrottleDevice(Action):
    
    def name (self) -> Text:
        return "action_unthrottle_device"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        url = "http://127.0.0.1:8000/unthrottle_device"

        try:
            device = tracker.get_slot("device")
            response = requests.post(url, json={"device": device})

            if response.status_code == 200:
                if response.json().get("message") == "success":
                    message = "Device has been unthrottled successfully."
                elif response.json().get("message") == "not_Present":
                    message = "Device is not currently being throttled."
                else:
                    message = "Device could not be unthrottled. Please check the device name and try again. Alternatively, ask to view current devices to specify using MAC instead."
            else:
                message = f"Error: Received {response.status_code} from the API."
        except Exception as e:
            message = f"Exception occured in Rasa Actions: {str(e)}"

        dispatcher.utter_message(text=message)
        return []

#--------------------------------------------------------------------------------------------------------------------
#ActionDeprioritiseDevice - Sends an input to the API to deprioritise a device's bandwidth
#--------------------------------------------------------------------------------------------------------------------
class ActionDeprioritiseDevice(Action):

    def name (self) -> Text:
        return "action_deprioritise_device"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        url = "http://127.0.0.1:8000/deprioritise_device"

        try:
            device = tracker.get_slot("device")
            response = requests.post(url, json={"device": device})

            if response.status_code == 200:
                if response.json().get("message") == "success":
                    message = "Device has been deprioritised successfully."
                elif response.json().get("message") == "not_Present":
                    message = "Device is not currently being prioritised."
                else:
                    message = "Device could not be deprioritised. Please check the device name and try again. Alternatively, ask to view current devices to specify using MAC instead."
            else:
                message = f"Error: Received {response.status_code} from the API."
        except Exception as e:
            message = f"Exception occured in Rasa Actions: {str(e)}"

        dispatcher.utter_message(text=message)
        return []

#--------------------------------------------------------------------------------------------------------------------
#ActionRetrieveThrottled - Used to return a list of all devices currently being throttled on the network
#--------------------------------------------------------------------------------------------------------------------
class ActionRetrieveThrottled(Action):

    def name (self) -> Text:
        return "action_retrieve_throttled_devices"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        url = "http://127.0.0.1:8000/get_throttled_devices"

        try:
            response = requests.get(url)

            if response.status_code == 200:
                data = response.json()
                throttled_devices = data.get("throttled_devices", [])
                message = "🌐 Here are the devices currently being throttled on the network: \n"        
                message += "  \n  "

                for device in throttled_devices:
                    mac, hostname = mac_translation(device)
                    if mac is None or hostname is None:
                        continue
                    message += f"• Device {hostname} (MAC: {mac}) is being throttled \n"

            else:
                message = f"Error: Received {response.status_code} from the API."
        except Exception as e:
            message = f"Exception occured in Rasa Actions: {str(e)}"

        dispatcher.utter_message(text=message)
        return []
    
#--------------------------------------------------------------------------------------------------------------------
#ActionRetrievePrioritised - Used to return a list of all devices currently being prioritised on the network
#--------------------------------------------------------------------------------------------------------------------
class ActionRetrievePrioritised(Action):
    
    def name (self) -> Text:
        return "action_retrieve_prioritised_devices"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        url = "http://127.0.0.1:8000/get_prioritised_devices"

        try:
            response = requests.get(url)

            if response.status_code == 200:
                data = response.json()
                prioritised_devices = data.get("prioritised_devices", [])
                message = "🌐 Here are the devices currently being prioritised on the network: \n"
                message += "  \n  "

                for device in prioritised_devices:
                    mac, hostname = mac_translation(device)
                    if mac is None or hostname is None:
                        continue
                    message += f"• Device {hostname} (MAC: {mac}) is being prioritised \n"

            else:
                message = f"Error: Received {response.status_code} from the API."
        except Exception as e:
            message = f"Exception occured in Rasa Actions: {str(e)}"

        dispatcher.utter_message(text=message)
        return []

#--------------------------------------------------------------------------------------------------------------------
#ActionRetrieveGuestList - Used to return the current list of guests or unknown devices on the network
#--------------------------------------------------------------------------------------------------------------------
class ActionRetrieveGuestList(Action):
    
    def name (self) -> Text:
        return "action_retrieve_guest_list"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        url = "http://127.0.0.1:8000/get_guest_list"

        try:
            response = requests.get(url)

            if response.status_code == 200:
                data = response.json()
                print(data)
                guest_list = data.get("guest_list", [])
                message = "☠️ These devices could be a newly connected device, a guest device or a potentially harmful device ☠️ \n"
                message += "🌐 Here are the devices currently on the network that are not recognised: \n"
                message += "  \n  "

                for device in guest_list:
                    mac, hostname = mac_translation(device)
                    if mac is None or hostname is None:
                        continue
                    message += f"• {hostname} (MAC: {mac}) \n"

                message += " \n ⚠️ You can unblock these devices by asking me to add them to the whitelist - use with caution ⚠️ \n"

            else:
                message = f"Error: Received {response.status_code} from the API."
        except Exception as e:
            message = f"Exception occured in Rasa Actions: {str(e)}"

        dispatcher.utter_message(text=message)
        return []
    
#--------------------------------------------------------------------------------------------------------------------
#ActionConfirmWhitelist - Used to confirm that a user wants to add a device to the whitelist
#--------------------------------------------------------------------------------------------------------------------
class ActionConfirmWhitelist(Action):
    
    def name (self) -> Text:
        return "action_confirm_whitelist"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        device = tracker.get_slot("device")
        message = f"Are you sure you want to add {device} to the whitelist?"
        message += " \n This will allow the device to connect to the network without being blocked"
        message += " \n This device has been marked as unknown, and so it may be potentially harmful"
        message += " \n Enter the password to confirm, or type 'cancel' to abort."

        dispatcher.utter_message(text=message)
        return []

#--------------------------------------------------------------------------------------------------------------------
#ActionAddToWhitelist - Used to add a device to the whitelist
#--------------------------------------------------------------------------------------------------------------------
class ActionAddToWhitelist(Action):
    
    def name (self) -> Text:
        return "action_whitelist_device"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        url = "http://127.0.0.1:8000/whitelist_device"

        try:
            device = tracker.get_slot("device")
            response = requests.post(url, json={"device": device})

            if response.status_code == 200:
                if response.json().get("message") == "success":
                    message = "Device has been added to the whitelist successfully."
                elif response.json().get("message") == "error":
                    message = "Device could not be whitelisted. Is it already on the whitelist?"
                elif response.json().get("message") == "wrong_type":
                    message = "Device must be specfifed using a MAC address, ensure you are using the correct format (AA:BB:CC:DD:EE:FF)."
                else:
                    message = "Device could not be added to the whitelist. Please check the MAC address is correct and try again."
            else:
                message = f"Error: Received {response.status_code} from the API."

        except Exception as e:
            message = f"Exception occured in Rasa Actions: {str(e)}"

#--------------------------------------------------------------------------------------------------------------------
# Helper function which accesses the API to translate a MAC address to a hostname
#--------------------------------------------------------------------------------------------------------------------

def mac_translation(input_str):
    
    url = "http://127.0.0.1:8000/mac_translation"

    input_value = input_str

    try:
        response = requests.post(url, json={"input_value": input_value})
        
        if response.status_code == 200:
            response_data = response.json() 
            mac = response_data.get("mac")
            hostname = response_data.get("hostname")
        else:
            print(f"Error: Received {response.status_code} from the API.")
            return None, None

    except Exception as e:
        message = f"Exception occured in Rasa Actions: {str(e)}"
        return None, None

    return mac, hostname
    