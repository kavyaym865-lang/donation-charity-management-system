# Donation & Charity Management System

A web-based college mini-project developed to simplify charity browsing, donor registration, and donation management using Python, Flask, HTML, and CSS.

## About the Project

The Donation & Charity Management System provides a platform where users can explore charity organizations, view charity details, register for an account, and follow a QR-code-based donation workflow. It also includes administrative pages for managing charity information and viewing donation records.

The project aims to make charity information easier to access and demonstrate how web technologies can support donation management.

## Features

- User registration and login
- Browse and view charity information
- Donation form with QR-code-based payment workflow
- Donation receipt pages
- Admin login and dashboard
- Charity and donation management interfaces

## Technologies Used

- **Backend:** Python, Flask
- **Frontend:** HTML, CSS
- **Database:** SQLite, if configured in the current application
- **Development Environment:** Visual Studio Code
- **QR Code:** QR-code image and supporting Python code

## Project Structure

- `app.py` — Main Flask application
- `requirements.txt` — Python dependencies
- `schema.sql` — Database schema
- `templates/` — HTML pages for users, donations, and administration
- `static/` — CSS, images, logos, and QR-code assets

## How to Run Locally

1. Install Python 3.
2. Clone or download this repository.
3. Open a terminal in the project folder.
4. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Start the application:

   ```bash
   python app.py
   ```

6. Open the local address displayed in the terminal in your browser.

Database setup may be required depending on the application's configuration.

## Academic Project Notice

This project was developed for academic purposes as a college mini-project. The QR-code payment workflow is intended for demonstration. Actual payment verification and successful transaction processing should not be assumed unless implemented and tested.

Use dummy data for demonstrations. Do not commit real donor information, database files containing private records, passwords, or payment API secret keys to a public repository.
