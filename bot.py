from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from sqlalchemy.orm import Session
from models import User, UserNameChange, Chat, Message
import os
from datetime import datetime
import logging
from init_db import init_database
import tempfile

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
RENDER_URL = os.environ.get('RENDER_URL')

class Bot:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.last_file_chat_id = None
        self.logger = logging.getLogger(__name__)
        # Extended Hindi to English character mapping
        self.hindi_to_eng = {
            # Basic vowels
            'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo',
            'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au', 'ऋ': 'ri',
            
            # Consonants
            'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
            'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
            'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
            'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
            'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
            'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'श': 'sh',
            'ष': 'sh', 'स': 's', 'ह': 'h', 'क्ष': 'ksh', 'त्र': 'tr',
            'ज्ञ': 'gy',
            
            # Matras (vowel signs)
            'ा': 'a', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo',
            'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ृ': 'ri',
            
            # Additional signs
            'ं': 'n', 'ः': 'h', '्': '', 'ँ': 'n', '़': '',
            'ॅ': 'en', 'ॆ': 'e', 'ॊ': 'o',
            
            # Numerals
            '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
            '५': '5', '६': '6', '७': '7', '८': '8', '९': '9',
            
            # Common combinations
            'क्क': 'kk', 'त्त': 'tt', 'ट्ट': 'tt', 'प्प': 'pp',
            'च्च': 'cch', 'ल्ल': 'll', 'ज्ज': 'jj', 'द्द': 'dd',
            'श्र': 'shr', 'त्र': 'tr', 'क्र': 'kr', 'प्र': 'pr',
            'ब्र': 'br', 'व्र': 'vr', 'ग्र': 'gr', 'द्र': 'dr',
            'ध्र': 'dhr', 'फ्र': 'fr', 'ह्र': 'hr',
            
            # Special combinations
            'क्य': 'ky', 'ख्य': 'khy', 'ग्य': 'gy', 'घ्य': 'ghy',
            'च्य': 'chy', 'ज्य': 'jy', 'त्य': 'ty', 'थ्य': 'thy',
            'द्य': 'dy', 'ध्य': 'dhy', 'न्य': 'ny', 'प्य': 'py',
            'ब्य': 'by', 'भ्य': 'bhy', 'म्य': 'my', 'व्य': 'vy',
            
            # Common words/sounds
            'श्री': 'shri', 'त्री': 'tri', 'स्त्री': 'stri',
            'क्त': 'kt', 'स्त': 'st', 'न्त': 'nt', 'र्त': 'rt',
            'स्थ': 'sth', 'स्व': 'sw', 'स्म': 'sm', 'ह्म': 'hm',
            'ह्य': 'hy', 'ह्व': 'hv', 'त्व': 'tv', 'न्न': 'nn',
            
            # Modern additions
            'ॐ': 'om', 'ऽ': "'", 'ड़': 'r', 'ढ़': 'rh',
            'य़': 'y', 'ऱ': 'r', 'ऴ': 'zh',
            
            # Common modern combinations
            'इं': 'in', 'उं': 'un', 'ऐं': 'ain', 'में': 'mein',
            'है': 'hai', 'हैं': 'hain', 'हों': 'hon', 'की': 'ki',
            'का': 'ka', 'को': 'ko', 'कि': 'ki', 'के': 'ke',
            
            # Additional modern sounds
            'ज़': 'z', 'फ़': 'f', 'ख़': 'kh', 'ग़': 'gh',
            'क़': 'q', 'व़': 'w',
            
            # Special characters
            '॰': '.', '॥': '||', '।': '|',
            
            # Common prefixes/suffixes
            'वाला': 'wala', 'वाली': 'wali', 'कार': 'kar',
            'पूर्व': 'purv', 'पूर्ण': 'purn', 'योग': 'yog',
        }
        
    def update_user_info(self, user_data):
        try:
            user = self.db.query(User).filter_by(user_id=user_data['User ID']).first()
            
            if user:
                # Check if name or username changed
                if (user.current_username != user_data['Username'] or
                    user.current_firstname != user_data['First Name'] or
                    user.current_lastname != user_data['Last Name']):
                    
                    # Record the change
                    name_change = UserNameChange(
                        user=user,
                        old_username=user.current_username,
                        old_firstname=user.current_firstname,
                        old_lastname=user.current_lastname
                    )
                    self.db.add(name_change)
                    
                    # Update current info
                    user.current_username = user_data['Username']
                    user.current_firstname = user_data['First Name']
                    user.current_lastname = user_data['Last Name']
            else:
                # Create new user
                user = User(
                    user_id=user_data['User ID'],
                    current_username=user_data['Username'],
                    current_firstname=user_data['First Name'],
                    current_lastname=user_data['Last Name']
                )
                self.db.add(user)
                
            self.db.commit()
            return user
        except Exception as e:
            self.logger.error(f"Error updating user info: {str(e)}")
            self.db.rollback()
            raise
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Hi! I'm waiting for temp_history.txt file.")
        
    def is_hindi(self, text):
        if not text:
            return False
        # Check if any character is in Hindi Unicode range (0900-097F)
        return any(ord('\u0900') <= ord(char) <= ord('\u097F') for char in text)

    def find_hindi_words(self, text):
        if not text:
            return set()
        # Split text into words and filter Hindi ones
        words = text.split()
        hindi_words = {word for word in words if self.is_hindi(word)}
        return hindi_words

    def transliterate_hindi(self, text):
        """Convert Hindi text to Roman/English characters"""
        result = ''
        skip_next = False
        for i, char in enumerate(text):
            if skip_next:
                skip_next = False
                continue
                
            if char in self.hindi_to_eng:
                # Look ahead for combined characters
                if i < len(text) - 1 and text[i + 1] in ['्', 'ा', 'ि', 'ी', 'ु', 'ू', 'े', 'ै', 'ो', 'ौ']:
                    combined = char + text[i + 1]
                    result += self.hindi_to_eng.get(combined, self.hindi_to_eng[char] + self.hindi_to_eng[text[i + 1]])
                    skip_next = True
                else:
                    result += self.hindi_to_eng[char]
            else:
                result += char
        return result

    async def process_history_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        temp_filename = None
        try:
            self.logger.info("Starting file processing")
            file = await context.bot.get_file(update.message.document.file_id)
            
            # Use tempfile module to handle file cleanup automatically
            with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as temp_file:
                temp_filename = temp_file.name
                await file.download_to_drive(temp_filename)
            
            # Clear existing data in correct order
            self.logger.info("Clearing existing data from database")
            try:
                self.db.query(UserNameChange).delete()
                self.db.query(Message).delete()
                self.db.query(Chat).delete()
                self.db.query(User).delete()
                self.db.commit()
                self.logger.info("Successfully cleared existing data")
            except Exception as e:
                self.db.rollback()
                self.logger.error(f"Error clearing data: {str(e)}")
                raise

            # Read and parse the file
            with open(temp_filename, "r", encoding='utf-8') as f:
                content = f.read()
            
            self.logger.info(f"File content length: {len(content)}")
            
            # Skip the header "ℹ️ Chat History:"
            if "ℹ️ Chat History:" in content:
                content = content.split("ℹ️ Chat History:")[1]
            
            # Split entries by the custom separator instead of Time:
            entries = []
            current_entry = []
            
            for line in content.strip().split('\n'):
                if line.strip() == "=" * 50:  # Our custom separator
                    if current_entry:
                        entries.append('\n'.join(current_entry))
                        current_entry = []
                    continue
                current_entry.append(line)
            
            if current_entry:  # Add the last entry
                entries.append('\n'.join(current_entry))
            
            self.logger.info(f"Entries collected for processing: {len(entries)}")
            
            # Track Hindi words and their transliterations
            hindi_word_transliterations = {}
            all_entries = []
            
            for entry_num, entry in enumerate(entries, 1):
                chat_info = {}
                lines = entry.strip().split('\n')
                
                # Log the raw entry content for debugging
                self.logger.info(f"\nProcessing Entry {entry_num}:\n")
                self.logger.info("-" * 50 + "\n")
                self.logger.info(f"Raw content:\n{entry}\n")
                
                for line in lines:
                    if ': ' in line:
                        key, value = line.split(': ', 1)
                        key = key.strip()
                        value = value.strip() if value else None
                        chat_info[key] = value
                
                if chat_info:  # Only add if we got valid data
                    all_entries.append((entry_num, chat_info))
                    # Find Hindi words in all text fields
                    for field in ['First Name', 'Last Name', 'Username', 'Chat Name', 'Message', 'Response']:
                        if field in chat_info and chat_info[field]:
                            hindi_words = self.find_hindi_words(chat_info[field])
                            for word in hindi_words:
                                if word not in hindi_word_transliterations:
                                    transliterated = self.transliterate_hindi(word)
                                    hindi_word_transliterations[word] = transliterated

                required_fields = ['Chat ID', 'Chat Type', 'User ID', 'Username', 'First Name', 'Message', 'Response']
                missing_fields = [field for field in required_fields if field not in chat_info]
                
                if missing_fields:
                    self.logger.info(f"SKIPPED - Missing fields: {', '.join(missing_fields)}")
                    self.logger.info("Found fields:")
                    for key, value in chat_info.items():
                        self.logger.info(f"  {key}: {value}")
                else:
                    self.logger.info("Processed successfully")
                
                self.logger.info("-" * 50 + "\n")
            
            self.logger.info("\nProcessing Summary:")
            self.logger.info(f"Total entries collected: {len(entries)}")
            self.logger.info(f"Successfully processed: {len(entries)}")
            self.logger.info(f"Skipped entries: {0}")
            
            if hindi_word_transliterations:
                # Split long transliteration messages
                MAX_MESSAGE_LENGTH = 4096  # Telegram's limit
                report_parts = ["Found Hindi words with suggested transliterations:\n"]
                current_part = report_parts[0]
                
                for hindi, eng in sorted(hindi_word_transliterations.items()):
                    line = f"{hindi}: {eng}\n"
                    if len(current_part) + len(line) > MAX_MESSAGE_LENGTH:
                        # Start new part
                        current_part += "\nContinued in next message..."
                        report_parts.append("Continuing Hindi words:\n")
                        current_part = report_parts[-1]
                    current_part += line
                
                # Add instructions to the last part
                report_parts[-1] += "\nReply with any corrections in format:\nword1:replacement1\nword2:replacement2"
                
                # Send all parts
                for part in report_parts:
                    await update.message.reply_text(part)
                
                # Store for later use
                context.user_data['all_entries'] = entries
                context.user_data['temp_filename'] = temp_filename
                context.user_data['transliterations'] = hindi_word_transliterations
                return
            
            required_fields = ['Chat ID', 'Chat Type', 'User ID', 'Username', 'First Name', 'Message', 'Response', 'Time']
            if all(k in chat_info for k in required_fields):
                try:
                    # Update or create chat
                    chat = self.db.query(Chat).filter_by(chat_id=chat_info['Chat ID']).first()
                    if not chat:
                        chat = Chat(
                            chat_id=chat_info['Chat ID'],
                            chat_type=chat_info['Chat Type'],
                            chat_name=chat_info.get('Chat Name')
                        )
                        self.db.add(chat)
                        self.db.flush()
                    
                    # Update or create user
                    user = self.update_user_info({
                        'User ID': chat_info['User ID'],
                        'Username': chat_info['Username'],
                        'First Name': chat_info['First Name'],
                        'Last Name': chat_info.get('Last Name'),
                    })
                    
                    # Parse timestamp
                    try:
                        timestamp = datetime.strptime(chat_info['Time'], '%Y-%m-%d %H:%M:%S.%f')
                    except ValueError:
                        timestamp = datetime.strptime(chat_info['Time'], '%Y-%m-%d %H:%M:%S')
                    
                    # Create message
                    message = Message(
                        user_id=user.id,
                        chat_id=chat.id,
                        message_text=chat_info['Message'],
                        response_text=chat_info['Response'],
                        timestamp=timestamp
                    )
                    self.db.add(message)
                    
                except Exception as e:
                    self.logger.error(f"Error processing entry {entry_num}: {str(e)}")
            
            if not all(k in chat_info for k in required_fields):
                missing = [k for k in required_fields if k not in chat_info]
                print(f"Entry {entry_num} missing fields: {missing}")
                print(f"Entry content:\n{entry}")
            
            self.db.commit()
            self.logger.info(f"Processing complete. Processed: {len(entries)}")
            self.last_file_chat_id = update.effective_chat.id
            await update.message.reply_text(
                f"DONE\nProcessed: {len(entries)}"
            )
            
        except Exception as e:
            self.logger.error(f"Error processing file: {str(e)}")
            self.db.rollback()
            await update.message.reply_text(f"Error processing file: {str(e)}")
        
        finally:
            # Clean up temp file
            if temp_filename and os.path.exists(temp_filename):
                try:
                    os.unlink(temp_filename)
                except Exception as e:
                    self.logger.error(f"Error cleaning up temp file: {str(e)}")
        
    async def handle_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if (update.message.reply_to_message and 
            "Found Hindi words with suggested transliterations:" in update.message.reply_to_message.text):
            
            if update.message.text.lower() == "papapiya":
                # Get stored entries and transliterations
                entries = context.user_data.get('all_entries', [])
                transliterations = context.user_data.get('transliterations', {})
                temp_filename = context.user_data.get('temp_filename')
                
                if not entries or not temp_filename:
                    await update.message.reply_text("Session expired. Please upload the file again.")
                    return
                
                valid_entries = 0
                skipped_entries = 0
                
                # Process all entries
                for entry_num, entry in enumerate(entries, 1):
                    chat_info = {}
                    lines = entry.strip().split('\n')
                    
                    # Parse entry into chat_info
                    for line in lines:
                        if ': ' in line:
                            key, value = line.split(': ', 1)
                            key = key.strip()
                            value = value.strip() if value else None
                            chat_info[key] = value
                    
                    # Apply transliterations to text fields
                    for field in ['First Name', 'Last Name', 'Username', 'Chat Name', 'Message', 'Response']:
                        if field in chat_info and chat_info[field]:
                            text = chat_info[field]
                            for hindi, english in transliterations.items():
                                text = text.replace(hindi, f"{english}*")
                            chat_info[field] = text
                    
                    # Process the modified entry
                    required_fields = ['Chat ID', 'Chat Type', 'User ID', 'Username', 'First Name', 'Message', 'Response']
                    if all(k in chat_info for k in required_fields):
                        try:
                            # Update or create chat
                            chat = self.db.query(Chat).filter_by(chat_id=chat_info['Chat ID']).first()
                            if not chat:
                                chat = Chat(
                                    chat_id=chat_info['Chat ID'],
                                    chat_type=chat_info['Chat Type'],
                                    chat_name=chat_info.get('Chat Name')
                                )
                                self.db.add(chat)
                                self.db.flush()
                            
                            # Update or create user
                            user = self.update_user_info({
                                'User ID': chat_info['User ID'],
                                'Username': chat_info['Username'],
                                'First Name': chat_info['First Name'],
                                'Last Name': chat_info.get('Last Name'),
                            })
                            
                            # Parse timestamp
                            try:
                                timestamp = datetime.strptime(chat_info['Time'], '%Y-%m-%d %H:%M:%S.%f')
                            except ValueError:
                                timestamp = datetime.strptime(chat_info['Time'], '%Y-%m-%d %H:%M:%S')
                            
                            # Create message
                            message = Message(
                                user_id=user.id,
                                chat_id=chat.id,
                                message_text=chat_info['Message'],
                                response_text=chat_info['Response'],
                                timestamp=timestamp
                            )
                            self.db.add(message)
                            valid_entries += 1
                            
                        except Exception as e:
                            self.logger.error(f"Error processing entry {entry_num}: {str(e)}")
                            skipped_entries += 1
                    else:
                        skipped_entries += 1
                
                self.db.commit()
                await update.message.reply_text(
                    f"DONE\nProcessed: {valid_entries}\n"
                    f"Skipped: {skipped_entries}"
                )
            else:
                await update.message.reply_text("To accept all transliterations, reply with 'papapiya'")
            
        elif (update.message.reply_to_message and 
              "DONE" in update.message.reply_to_message.text and
              update.message.text.lower() == "papapiya"):
            await update.message.reply_text(f"Here's your URL: {RENDER_URL}")

    def create_history_file(self, messages):
        history = []
        for msg in messages:
            history.append(f"Time: {msg.timestamp}")
            history.append(f"Chat ID: {msg.chat.chat_id}")
            history.append(f"Chat Type: {msg.chat.chat_type}")
            history.append(f"User ID: {msg.user.user_id}")
            history.append(f"Username: @{msg.user.current_username}" if msg.user.current_username else "Username: None")
            history.append(f"First Name: {msg.user.current_firstname}")
            history.append(f"Last Name: {msg.user.current_lastname}")
            history.append(f"Message: {msg.message_text}")
            history.append(f"Response: {msg.response_text}")
            history.append("\n" + "="*50 + "\n")
        
        return "\n".join(history)

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message.document:
            return
        
        temp_file = None
        output_file = None
        try:
            # Get file from Telegram
            file = await context.bot.get_file(update.message.document.file_id)
            
            # Download to temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
            await file.download_to_drive(temp_file.name)
            temp_file.close()  # Close the file explicitly
            
            # If this is a history file being uploaded for processing
            if update.message.document.file_name == "temp_history.txt":
                await self.process_history_file(update, context)
                os.unlink(temp_file.name)
                return
                
            # Otherwise, create new history file with translations
            messages = self.db.query(Message).order_by(Message.timestamp.desc()).limit(100).all()
            history_text = self.create_history_file(messages)
            
            # Write to new file
            output_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8')
            output_file.write(history_text)
            output_file.close()  # Close the file explicitly
            
            # Send file using a context manager
            with open(output_file.name, 'rb') as f:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=f,
                    filename='chat_history_with_translations.txt'
                )
            
            # Clean up
            if temp_file and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            if output_file and os.path.exists(output_file.name):
                os.unlink(output_file.name)
            
        except Exception as e:
            self.logger.error(f"Error handling document: {str(e)}")
            await update.message.reply_text(f"Error processing file: {str(e)}")
        
        finally:
            # Additional cleanup in case of errors
            try:
                if temp_file and os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
                if output_file and os.path.exists(output_file.name):
                    os.unlink(output_file.name)
            except Exception as e:
                self.logger.error(f"Error in cleanup: {str(e)}")

def main():
    # Initialize database and create session
    engine, SessionLocal = init_database()
    db_session = SessionLocal()
    
    # Create bot with database session
    bot = Bot(db_session=db_session)
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(MessageHandler(filters.Document.ALL, bot.handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_reply))
    
    application.run_polling()

if __name__ == '__main__':
    main() 