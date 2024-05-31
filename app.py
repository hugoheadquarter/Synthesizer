import streamlit as st
import pymupdf  # Correct import for PyMuPDF
import re
import google.generativeai as genai

# Default prompt
default_prompt = """
Here is the raw text from a book:

<book_text>
{book_text}
</book_text>

Please read through the text carefully. Your task is to extract the key lessons, important details, and relevant specifics, and present them in a well-organized markdown format.

Specifically, look for:
- Key concepts, theories, mental models, frameworks, methods and ideas
- Illuminating anecdotes, examples or stories that illustrate the main points
- Specific action items, exercises, or how-to steps the reader can take
- Relevant details that add depth and context to the key lessons
- **Direct quotes from the book that powerfully capture key points**

Organize the information you extract into sections with clear headings. 
Begin each key concept section with an introductory paragraph that provides an overview, context, and significance of the concept being discussed. This introductory paragraph is crucial and should always be included. Then, thoroughly present the relevant lessons and details - liberal use of bulletpoints and sub-bullets is encouraged to structure the information and capture all important specifics.
Include both the high-level takeaways as well as noteworthy details and examples. Err on the side of over-including relevant details and examples rather than excluding them. Minor points can be included if they help illustrate or support major lessons.
The goal is to create a comprehensive resource that captures not only the essential knowledge from the book, but also the key supporting information, details, examples and quotes. The final deliverable should be organized in an easy to reference format with a hierarchy of information. 
Write your markdown-formatted response extracting and presenting the book's key lessons, concepts, examples, action items, relevant details, and powerful quotes inside <markdown> tags. Utilize tables where appropriate to enhance clarity and readability.

Here is an example of the desired format for your response:

<markdown>

## Introduction
[Overview of the main themes, ideas, or concepts]

## Key Concept 1
[This introduction paragraph providing an overview, context, and significance of Key Concept 1 should always be included]
- Detail 1a
- Detail 1b
  - Sub-detail 1b1
  - Sub-detail 1b2
- Detail 1c 
> "Relevant quote 1" - Author

## Key Concept 2
[This introduction paragraph providing an overview, context, and significance of Key Concept 2 should always be included]
- Detail 2a
- Detail 2b
  - Sub-detail 2b1
    - Sub-sub-detail 2b1a
  - Sub-detail 2b2
> "Relevant quote 2" - Author

Etc.

</markdown>
"""

# Function to extract chapters from PDF
def extract_chapters(file_content):
    chapters = {}
    current_text = []

    try:
        doc = pymupdf.open("pdf_file", file_content)  # open the document from the in-memory file
        for page in doc:  # iterate the document pages
            text = page.get_text()  # get plain text
            current_text.append(text)
        
        full_text = "\n".join(current_text)
        chapters_list = full_text.split("CHAPTER ")

        for i, chapter in enumerate(chapters_list[1:], start=1):  # skip the first split part
            if chapter.strip():  # ignore empty strings
                chapters[f"CHAPTER {i}"] = "CHAPTER " + chapter.strip()

    except Exception as e:
        st.error(f"An error occurred: {e}")

    return chapters, full_text

# Function to get key ideas using Google Gemini API
def get_key_ideas(chapter_text, api_key, prompt):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-pro')
    prompt = prompt.replace("{book_text}", chapter_text)
    try:
        response = model.generate_content(prompt)
        print(response)
        result = response.candidates[0].content.parts[0].text
        # Extract content between <markdown> tags using regex
        match = re.search(r'<markdown>(.*?)</markdown>', result, re.IGNORECASE | re.DOTALL)
        if match:
            key_ideas = match.group(1).strip()
        else:
            key_ideas = None
        
        return key_ideas
    except Exception as e:
        st.error(f"Error in Gemini API call: {str(e)}")
        return None

# Initialize session state variables
if 'api_key' not in st.session_state:
    st.session_state['api_key'] = ''

if 'uploaded_file_content' not in st.session_state:
    st.session_state['uploaded_file_content'] = None

if 'custom_prompt' not in st.session_state:
    st.session_state['custom_prompt'] = default_prompt

# Streamlit app
st.title("Book Lesson Extractor")

# Sidebar selection
page = st.sidebar.radio("Select Page", ("Home", "Prompt"))

if page == "Home":
    # Sidebar for file upload
    uploaded_file = st.sidebar.file_uploader("Upload a PDF file", type="pdf")
    if uploaded_file is not None:
        # Store the uploaded file content in session state
        st.session_state['uploaded_file_content'] = uploaded_file.read()

    # Sidebar for API key input at the bottom
    st.session_state['api_key'] = st.sidebar.text_input("Enter your Google Gemini API key", value=st.session_state['api_key'])

    if st.session_state['uploaded_file_content']:
        chapters_dict, full_text = extract_chapters(st.session_state['uploaded_file_content'])
        
        # Dropdown menu for chapter selection
        chapter_options = ["ALL"] + list(chapters_dict.keys())
        selected_chapter = st.sidebar.selectbox("Select Chapter", chapter_options)
        
        if selected_chapter:
            # Display selected chapter raw text
            raw_text_placeholder = st.empty()
            if selected_chapter == "ALL":
                raw_text_placeholder.write(full_text)
            else:
                raw_text_placeholder.write(chapters_dict[selected_chapter])
        
        # Extract button
        if st.sidebar.button("Extract Lessons"):
            # Clear the raw text and show extracting message
            raw_text_placeholder.empty()
            extracting_message = st.warning("Extracting key lessons...")

            # Display selected chapter text
            if selected_chapter == "ALL":
                key_ideas = get_key_ideas(full_text, st.session_state['api_key'], st.session_state['custom_prompt'])
            else:
                key_ideas = get_key_ideas(chapters_dict[selected_chapter], st.session_state['api_key'], st.session_state['custom_prompt'])

            # Show success message and display key ideas
            extracting_message.empty()
            if key_ideas is None:
                st.error("Could not extract the lessons.")
            else:
                st.success("Key lessons extracted!")
                st.markdown(key_ideas)
    else:
        st.write("Please upload a PDF file using the sidebar.")

elif page == "Prompt":
    st.markdown('<span style="color:yellow;">**WARNING:** You NEED to mention &lt;book_text&gt;&lt;/book_text&gt; and &lt;markdown&gt;&lt;/markdown&gt; tags in the prompt. Make sure to press Save to apply changes', unsafe_allow_html=True)
    prompt = st.text_area("Edit the prompt below:", value=st.session_state['custom_prompt'], height=400)
    
    if st.button("Save"):
        st.session_state['custom_prompt'] = prompt
        st.success("Prompt saved!")
