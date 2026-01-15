# actions.py - FIXED FOR PRODUCTION (Railway) + Django API
from typing import Any, Text, Dict, List, Optional
import os
import requests

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from rasa_sdk.forms import FormValidationAction

# ✅ Django API base (set this in Railway variables)
# Example: https://reclamation-backend-production.up.railway.app/api
DJANGO_API_BASE = os.environ.get("DJANGO_API_BASE", "http://127.0.0.1:8000/api").rstrip("/")


class ValidateReclamationForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_reclamation_form"

    async def validate_email(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        if not slot_value or not str(slot_value).strip():
            return {"email": None}

        email = str(slot_value).strip()
        if "@" not in email or "." not in email:
            dispatcher.utter_message(text="Please provide a valid email address (e.g., name@example.com).")
            return {"email": None}

        return {"email": email}

    async def validate_phone(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        if not slot_value or not str(slot_value).strip():
            return {"phone": None}

        phone = str(slot_value).strip()
        digits = "".join(filter(str.isdigit, phone))
        if len(digits) < 5:
            dispatcher.utter_message(text="Please provide a valid phone number with at least 5 digits.")
            return {"phone": None}

        return {"phone": phone}

    async def validate_username(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        if not slot_value or len(str(slot_value).strip()) < 2:
            dispatcher.utter_message(text="Please provide a valid username (at least 2 characters).")
            return {"username": None}

        username = str(slot_value).strip()
        if username.isdigit():
            dispatcher.utter_message(text="That looks like an ID. Please provide your username instead.")
            return {"username": None}

        return {"username": username}

    async def validate_reclamation_message(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        if not slot_value or len(str(slot_value).strip()) < 10:
            dispatcher.utter_message(text="Please provide more details about your issue (at least 10 characters).")
            return {"reclamation_message": None}

        return {"reclamation_message": str(slot_value).strip()}


class ActionSubmitReclamation(Action):
    def name(self) -> Text:
        return "action_submit_reclamation"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        username: Optional[str] = tracker.get_slot("username")
        reclamation_message: Optional[str] = tracker.get_slot("reclamation_message")
        email: Optional[str] = tracker.get_slot("email")
        phone: Optional[str] = tracker.get_slot("phone")

        data = {
            "username": username if username else "Anonymous",
            "message": reclamation_message if reclamation_message else "",
            "category": "Rasa Bot",
            "location": "Rasa Chat Interface",
        }

        if email and str(email).strip():
            data["email"] = str(email).strip()

        if phone and str(phone).strip():
            data["phone"] = str(phone).strip()

        try:
            url = f"{DJANGO_API_BASE}/reclamations/add/"
            response = requests.post(url, json=data, timeout=15)

            if response.status_code == 201:
                response_data = response.json()
                rec_id = response_data.get("id", "Unknown")

                priority = str(response_data.get("priority", "normal")).upper()
                sentiment = str(response_data.get("sentiment", "neutral")).capitalize()

                contact_info = ""
                if email and str(email).strip():
                    contact_info += f"\n📧 Email: {email}"
                if phone and str(phone).strip():
                    contact_info += f"\n📞 Phone: {phone}"

                success_message = (
                    f"✅ Reclamation submitted successfully!{contact_info}\n\n"
                    f"📋 Reclamation ID: #{rec_id}\n"
                    f"👤 Username: {username or 'Anonymous'}\n"
                    f"📝 Issue: {str(reclamation_message)[:100]}...\n"
                    f"🚨 Priority: {priority}\n"
                    f"😊 Sentiment: {sentiment}\n\n"
                    f"We will review your issue and contact you soon."
                )

                dispatcher.utter_message(text=success_message)
                return [SlotSet("reclamation_id", str(rec_id))]

            # If backend returns validation errors, show them
            try:
                error_json = response.json()
                dispatcher.utter_message(
                    text=f"❌ Error submitting reclamation (HTTP {response.status_code}). Details: {error_json}"
                )
            except Exception:
                dispatcher.utter_message(
                    text=f"❌ Error submitting reclamation (HTTP {response.status_code}). Please try again."
                )

            return []

        except requests.exceptions.Timeout:
            dispatcher.utter_message(text="❌ Django API timeout. Please try again later.")
            return []
        except Exception:
            dispatcher.utter_message(text="❌ Could not connect to the Django server. Please try again later.")
            return []


class ActionTrackReclamation(Action):
    def name(self) -> Text:
        return "action_track_reclamation"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        reclamation_id: Optional[str] = tracker.get_slot("reclamation_id")

        if not reclamation_id:
            dispatcher.utter_message(text="Please provide your reclamation ID.")
            return []

        try:
            url = f"{DJANGO_API_BASE}/reclamations/{reclamation_id}/"
            r = requests.get(url, timeout=15)

            if r.status_code == 200:
                data = r.json()

                dispatcher.utter_message(
                    text=(
                        f"📊 Reclamation #{data.get('id', reclamation_id)}\n"
                        f"Status: {data.get('status', 'unknown')}\n"
                        f"Priority: {data.get('priority', 'normal')}\n"
                        f"Sentiment: {data.get('sentiment', 'neutral')}\n"
                        f"Message: {str(data.get('message', ''))[:150]}"
                    )
                )
                return []

            if r.status_code == 404:
                dispatcher.utter_message(text="❌ No reclamation found with that ID.")
                return []

            dispatcher.utter_message(text=f"❌ Tracking error (HTTP {r.status_code}). Please try again.")
            return []

        except requests.exceptions.Timeout:
            dispatcher.utter_message(text="❌ Django API timeout while tracking. Please try again later.")
            return []
        except Exception:
            dispatcher.utter_message(text="❌ Could not connect to the Django server. Please try again later.")
            return []
