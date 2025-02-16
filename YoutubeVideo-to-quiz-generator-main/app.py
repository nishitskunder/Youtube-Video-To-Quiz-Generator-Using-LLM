import streamlit as st
import json
import os
from dotenv import load_dotenv
from langchain_community.document_loaders import YoutubeLoader
from openai import OpenAI

# Load environment variables
load_dotenv()
OpenAI.api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI()

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

@st.cache_data
def fetch_questions(text_content, quiz_level, num_questions):
    """
    Fetch MCQ questions from OpenAI based on the provided text content, quiz level, and the number of questions.
    """
    RESPONSE_JSON = {
        "mcqs": [
            {
                "mcq": "What is an example question?",
                "options": {
                    "a": "Example option 1",
                    "b": "Example option 2",
                    "c": "Example option 3",
                    "d": "Example option 4",
                },
                "correct": "a",
            },
        ]
    }

    PROMPT_TEMPLATE = f"""
    Text: {text_content}
    You are an expert in generating MCQ type quizzes based on the provided content.
    Given the above text, create a quiz of {num_questions} multiple-choice questions keeping difficulty level as {quiz_level}.
    Your response must be **strictly valid JSON** matching the schema below:
    {json.dumps(RESPONSE_JSON, indent=2)}
    Do not include any extra text or explanation, only the JSON.
    """

    try:
        # Make the API call
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": PROMPT_TEMPLATE}],
            temperature=0.3,
            max_tokens=1500,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
        )

        # Extract the response
        extracted_response = response.choices[0].message.content.strip()

        # Clean up the response to remove backticks
        if extracted_response.startswith("```json"):
            extracted_response = extracted_response[7:]  # Remove "```json"
        if extracted_response.endswith("```"):
            extracted_response = extracted_response[:-3]  # Remove ending "```"

        # Parse the cleaned response
        return json.loads(extracted_response).get("mcqs", [])
    except json.JSONDecodeError as e:
        st.error("Failed to decode the response from OpenAI. Please try again.")
        print("Invalid JSON response:", extracted_response)
        print("JSONDecodeError:", str(e))
        return []
    except Exception as e:
        st.error("An error occurred while fetching questions. Please try again.")
        print("Error:", str(e))
        return []


@st.cache_data
def get_youtube_transcript(youtube_url):
    """
    Fetch the transcript of a YouTube video using YoutubeLoader.
    """
    try:
        loader = YoutubeLoader.from_youtube_url(youtube_url, add_video_info=False)
        transcript_data = loader.load()
        return transcript_data[0].page_content if transcript_data else ""
    except Exception as e:
        st.error("Failed to fetch YouTube transcript.")
        print("Transcript fetch error:", str(e))
        return ""


def main():
    """
    Main function to render the Streamlit app.
    """
    st.title("YouTube Quiz Generator")
    st.markdown(
        "This app generates quizzes based on the transcript of a YouTube video. Enter the video URL, select a difficulty level, and choose how many questions you want!"
    )

    # Initialize session state
    if "questions" not in st.session_state:
        st.session_state.questions = []
    if "selected_answers" not in st.session_state:
        st.session_state.selected_answers = []
    if "submitted" not in st.session_state:
        st.session_state.submitted = False

    # Input for YouTube URL
    youtube_url = st.text_input("Enter YouTube URL:")

    # Dropdown for selecting quiz level
    quiz_level = st.selectbox("Select quiz level:", ["Easy", "Medium", "Hard"])
    quiz_level_lower = quiz_level.lower()

    # Slider to select the number of quiz questions
    num_questions = st.slider("Select the number of quiz questions:", min_value=3, max_value=10, value=5)

    # Generate Quiz button
    if st.button("Generate Quiz"):
        if not youtube_url:
            st.error("Please enter a valid YouTube URL.")
            return

        # Fetch transcript
        st.info("Fetching video transcript...")
        transcript = get_youtube_transcript(youtube_url)

        if not transcript:
            st.error("Could not fetch transcript. Please check the URL or try another video.")
            return

        # Fetch questions
        st.info(f"Generating {num_questions} quiz questions based on the video transcript...")
        questions = fetch_questions(text_content=transcript, quiz_level=quiz_level_lower, num_questions=num_questions)

        if not questions:
            st.error("Failed to generate quiz. Please try again.")
            return

        # Store questions in session state
        st.session_state.questions = questions
        st.session_state.selected_answers = [None] * len(questions)
        st.session_state.submitted = False

    # Display quiz questions
    if st.session_state.questions:
        st.header("Quiz")
        for i, question in enumerate(st.session_state.questions):
            options = list(question["options"].values())
            selected_option = st.radio(
                question["mcq"],
                options,
                index=options.index(st.session_state.selected_answers[i]) if st.session_state.selected_answers[i] else 0,
                key=f"q{i}",
            )
            st.session_state.selected_answers[i] = selected_option

        # Submit button
        if st.button("Submit"):
            st.session_state.submitted = True

    # Display quiz results
    if st.session_state.submitted:
        marks = 0
        st.header("Quiz Results")
        for i, question in enumerate(st.session_state.questions):
            selected_option = st.session_state.selected_answers[i]
            correct_option = question["options"][question["correct"]]
            st.subheader(f"Q: {question['mcq']}")
            st.write(f"You selected: {selected_option}")
            st.write(f"Correct answer: {correct_option}")
            if selected_option == correct_option:
                marks += 1

        st.subheader(f"Your Score: {marks}/{len(st.session_state.questions)}")


if __name__ == "__main__":
    
    main()
