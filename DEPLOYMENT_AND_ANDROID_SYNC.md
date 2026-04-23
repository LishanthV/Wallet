# Trackify: Android Sync & Deployment Guide

## 1. Android Live Notification Sync (Using MacroDroid)

We have built a secure REST API into Trackify. Instead of relying purely on Gmail (which has a slight delay), you can use an Android automation app to catch notifications from GPay or PhonePe the *exact second* they appear and send them to your dashboard.

### Setup Instructions
1. Restart your Trackify server (`python app.py`).
2. Go to your **Trackify Settings Page**. You will now see your **Secret API Token** listed under the "Android Live Sync" integration.
3. Download **MacroDroid** from the Google Play Store on your Android phone.
4. Create a new Macro:
   - **Trigger**: Notification Present -> Select Application (e.g., GPay / PhonePe) -> Contains text "paid" or "sent".
   - **Action**: HTTP Request
     - **URL**: `http://YOUR_COMPUTER_IP:5000/api/sync/android` (We will update this URL once you deploy to the internet!)
     - **Method**: POST
     - **Content-Type**: application/json
     - **Body**:
       ```json
       {
         "api_token": "YOUR_SECRET_API_TOKEN_FROM_SETTINGS",
         "amount": "[notification_title]",
         "title": "GPay Payment"
       }
       ```
     *(Note: You can use MacroDroid's regex extraction features to perfectly parse the amount from the notification body).*

---

## 2. Deploying Trackify to the Internet

Currently, Trackify runs locally on your computer (`127.0.0.1:5000`). To access it from your phone anywhere in the world and make the Android Sync work over the cellular network, you need to host it!

### Recommended Free/Cheap Tech Stack
- **Web Hosting:** Render.com (Free Tier) or PythonAnywhere.
- **Database Hosting:** Aiven.io (Free MySQL Database) or PlanetScale.

### Steps to Deploy (Example using Render.com):
1. **Prepare the Repository**: You already have your project tracked in Git. Push your code to a private GitHub repository.
2. **Create a MySQL Database**: Sign up for Aiven.io, create a free MySQL database, and get the connection string.
3. **Deploy Web App**:
   - Go to Render.com and create a new "Web Service".
   - Connect your GitHub repository.
   - Start Command: `gunicorn app:app` (You will need to run `pip install gunicorn` and add it to your `requirements.txt`).
4. **Environment Variables**:
   In your Render dashboard, add the following Environment Variables so you don't expose secrets:
   - `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` (From your Aiven database)
   - `SMTP_USER`, `SMTP_PASSWORD` (Your Gmail credentials)
   - `FLASK_ENV` = `production`

Once deployed, Render will give you a live URL like `https://trackify-app.onrender.com`. You will use THIS URL in your Android MacroDroid app!
