# app.py

import streamlit as st
import re
import pandas as pd
import plotly.express as px
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# --- Helper Functions ---

# --- Helper Functions ---

# --- Helper Functions ---

def parse_chat(chat_file):
    """
    Parses an exported WhatsApp chat file, correctly handling multi-line messages.
    
    Args:
        chat_file: The uploaded file object.
        
    Returns:
        A pandas DataFrame with columns ['timestamp', 'sender', 'message'].
    """
    # Regex to find the start of any new message (date, time, and sender)
    # This pattern is the delimiter for splitting the entire chat file.
    # It looks for the opening bracket, date, comma, time, closing bracket, and the sender's name.
    line_start_pattern = re.compile(r'\[\d{1,2}/\d{1,2}/\d{2,4},\s\d{1,2}:\d{2}:\d{2}\s?[APap]?\.?[Mm]?\.?\]\s[^:]+:')
    
    # Get the full content of the file
    content = chat_file.getvalue().decode('utf-8')
    
    # Split the content by the message start pattern. This separates the chat into individual messages.
    messages = line_start_pattern.split(content)
    
    # The first element of the split is usually an empty string or the initial encryption message, so we skip it.
    if len(messages) > 1:
        messages = messages[1:]
    else:
        st.error("Could not find any messages in the file. The format might be incorrect.")
        return pd.DataFrame()
        
    # Find all the timestamp/sender lines which will act as our keys
    timestamps_and_senders = line_start_pattern.findall(content)

    if len(timestamps_and_senders) != len(messages):
        st.error("Parsing error: Mismatch between message headers and content. The chat file might be corrupted.")
        return pd.DataFrame()

    chat_data = []
    
    # Regex to extract the details from the timestamp/sender line
    details_pattern = re.compile(
        r'\[(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2}:\d{2}[\s\u202f]?[APap]?\.?[Mm]?\.?)\]\s([^:]+):'
    )

    for i in range(len(messages)):
        header = timestamps_and_senders[i]
        message_body = messages[i].strip()
        
        match = details_pattern.match(header)
        if match:
            date, time, sender = match.groups()
            
            # Clean up time string and combine with date
            time = time.replace('\u202f', ' ').strip()
            timestamp_str = f"{date} {time}"
            
            # Try parsing the timestamp
            try:
                # Format for '14/05/25, 9:33:53 PM'
                timestamp = pd.to_datetime(timestamp_str, format='%d/%m/%y, %I:%M:%S %p', errors='raise')
            except ValueError:
                try:
                    # Fallback for 24-hour format or other variations
                    timestamp = pd.to_datetime(timestamp_str, format='%d/%m/%Y, %H:%M:%S', errors='raise')
                except ValueError:
                    continue # Skip this message if timestamp is unparseable
            
            chat_data.append([timestamp, sender.strip(), message_body])

    if not chat_data:
        st.error("Failed to parse any valid messages. Please ensure the file is a standard WhatsApp chat export.")
        return pd.DataFrame()

    df = pd.DataFrame(chat_data, columns=['timestamp', 'sender', 'message'])
    df = df.dropna(subset=['timestamp'])
    return df

def analyze_romance(df, romantic_words):
    """
    Counts the frequency of romantic words in the chat messages.
    
    Args:
        df (pd.DataFrame): The chat DataFrame.
        romantic_words (list): A list of romantic words to search for.
        
    Returns:
        A pandas DataFrame with word counts.
    """
    word_counts = {word: 0 for word in romantic_words}
    
    for message in df['message']:
        for word in romantic_words:
            if word in message.lower():
                word_counts[word] += 1
                
    # Convert dictionary to DataFrame for plotting
    romance_df = pd.DataFrame(list(word_counts.items()), columns=['word', 'count'])
    romance_df = romance_df[romance_df['count'] > 0].sort_values(by='count', ascending=False)
    return romance_df

def create_wordcloud(df):
    """
    Generates and displays a word cloud from messages.
    
    Args:
        df (pd.DataFrame): The chat DataFrame.
    """
    text = ' '.join(df['message'].dropna())
    
    # Exclude common media-related words
    stopwords = set(['media', 'omitted', 'image', 'video'])
    
    if not text.strip():
        st.write("Not enough text to generate a word cloud.")
        return

    wordcloud = WordCloud(
        width=800, 
        height=400, 
        background_color='white',
        stopwords=stopwords,
        min_font_size=10
    ).generate(text)
    
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    st.pyplot(fig)


# --- Streamlit App UI ---

st.set_page_config(page_title="Couple's Chat Analyzer", layout="wide")

st.title("💑 Couple's Chat Analyzer")
st.markdown("Visualize the romance and fun in your chats!")

# List of romantic words to look for. You can customize this!
ROMANTIC_WORDS = [
    'love', 'miss you', 'hug', 'kiss', 'darling', 'sweetheart', 
    'honey', 'babe', 'my love', 'beautiful', 'handsome', 'amazing'
]

# --- Sidebar for setup and navigation ---
st.sidebar.header("Setup & Navigation")
uploaded_file = st.sidebar.file_uploader("Upload your WhatsApp chat file (.txt)", type="txt")

# Main container to hold the analysis
main_container = st.container()

if uploaded_file:
    df = parse_chat(uploaded_file)
    
    if not df.empty:
        # Get unique senders from the chat
        participants = df['sender'].unique().tolist()
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("Identify the Partners")
        
        # Select boxes to identify husband and wife
        husband_name = st.sidebar.selectbox("Who is the Husband?", participants, index=0)
        wife_name = st.sidebar.selectbox("Who is the Wife?", participants, index=1 if len(participants) > 1 else 0)
        
        if husband_name == wife_name:
            st.warning("Please select two different people.")
        else:
            # Filter DataFrames for each person
            df_husband = df[df['sender'] == husband_name]
            df_wife = df[df['sender'] == wife_name]
            
            # --- Page Navigation ---
            st.sidebar.markdown("---")
            page = st.sidebar.radio(
                "Choose a page to view",
                ("Overall Analysis", f"{husband_name}'s Analysis", f"{wife_name}'s Analysis")
            )
            
            # --- Display selected page content ---
            if page == "Overall Analysis":
                with main_container:
                    st.header("💖 Overall Romance Analysis")
                    st.markdown("Here's how often romantic words were used in the entire conversation.")
                    
                    romance_df = analyze_romance(df, ROMANTIC_WORDS)
                    
                    if not romance_df.empty:
                        fig = px.bar(romance_df, x='word', y='count', title="Frequency of Romantic Words", labels={'word': 'Romantic Word', 'count': 'Frequency'})
                        st.plotly_chart(fig)
                    else:
                        st.info("No romantic words from the list were found in the chat. Try adding more words!")

                    st.header("☁️ Overall Word Cloud")
                    st.markdown("The most common words used by both of you.")
                    create_wordcloud(df)

            elif page == f"{husband_name}'s Analysis":
                with main_container:
                    st.header(f"🤵‍♂️ {husband_name}'s Romance Analysis")
                    st.markdown(f"Romantic words used by {husband_name}.")

                    romance_df_husband = analyze_romance(df_husband, ROMANTIC_WORDS)
                    
                    if not romance_df_husband.empty:
                        fig = px.bar(romance_df_husband, x='word', y='count', title=f"Frequency of Romantic Words by {husband_name}", labels={'word': 'Romantic Word', 'count': 'Frequency'})
                        st.plotly_chart(fig)
                    else:
                        st.info(f"{husband_name} didn't use any of the tracked romantic words.")
                        
                    st.header(f"☁️ {husband_name}'s Word Cloud")
                    st.markdown(f"The most common words used by {husband_name}.")
                    create_wordcloud(df_husband)

            elif page == f"{wife_name}'s Analysis":
                with main_container:
                    st.header(f"👰‍♀️ {wife_name}'s Romance Analysis")
                    st.markdown(f"Romantic words used by {wife_name}.")
                    
                    romance_df_wife = analyze_romance(df_wife, ROMANTIC_WORDS)

                    if not romance_df_wife.empty:
                        fig = px.bar(romance_df_wife, x='word', y='count', title=f"Frequency of Romantic Words by {wife_name}", labels={'word': 'Romantic Word', 'count': 'Frequency'})
                        st.plotly_chart(fig)
                    else:
                        st.info(f"{wife_name} didn't use any of the tracked romantic words.")

                    st.header(f"☁️ {wife_name}'s Word Cloud")
                    st.markdown(f"The most common words used by {wife_name}.")
                    create_wordcloud(df_wife)
else:
    with main_container:
        st.info("👋 Welcome! Please upload a chat file on the left to get started.")

