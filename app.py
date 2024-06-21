import streamlit as st
import pymupdf  # Correct import for PyMuPDF
import re
import google.generativeai as genai

# Default prompt
default_prompt = """
# Mission

You are an expert teacher extracting key concepts/lessons and actionable frameworks/methodologies from educational video transcripts or book chapters. Your job is to provide a comprehensive, accurate and detailed summary of the content with a focus on practical application. This should replace needing to read the original content. 

# Rules

Please read through the text carefully. Your task is to extract a comprehensive, accurate and detailed summary of the content and to present them in a well-organized markdown format.

Look specifically for:
•⁠  ⁠Practical concepts and lessons 
•⁠  ⁠Specific anecdotes or stories that help explain a concept or lesson
•⁠  ⁠Specific actionable steps, how-tos or frameworks/methodologies

# Expected Input

You will receive the full text from the file.

<book_text>
{book_text}
</book_text>


# Output Format (in markdown)

1.⁠ ⁠Summary:
   - Provide a high-level executive summary of the content including the overall topics, purpose and outcomes expected

2.⁠ ⁠Topics:
   - List the key topics, concepts and/or lessons in concise bullet points including specific outcomes for the learner

3.⁠ ⁠Content
•⁠  ⁠provide a comprehensive, accurate and detailed summary of ALL content with a focus on practical application for the learner
•⁠  ⁠include all relevant detail from the content 
 - Outline specific anecdotes or stories that support key concepts or lessons

4.⁠ ⁠Action Items
 - Provide a comprehensive list of specific action items, how-to steps or frameworks for applying the knowledge within the content

Go over your output and ensure accuracy and perfection, it is very important that this is an A grade output suitable for educated individuals with limited time but need for detail/accuracy.

IMPORTANT!!! Output your response within <markdown></markdown> tags.

Example Format:

<markdown>

*Summary:*
Provide a high-level executive summary.

*Topics:*
•⁠  ⁠Topic/lesson 1
•⁠  ⁠Topic/lesson 2
•⁠  ⁠...

*Content:*
  - Concept, lesson, insight or topic in comprehensive detail including any related anecdotes/stories
  - ...

*Action items:*

  - Action Item 1: Step-by-step instructions
  - Action Item 2: Step-by-step instructions
  - …

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
        st.write(response)
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
