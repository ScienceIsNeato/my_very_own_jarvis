import json
import os
import openai
import time
import requests
from logger import Logger

def generate_filtered_story(context, style, story_title, query_dispatcher):
    """
    Generates a filtered story based on the provided context and style using ChatGPT.
    
    Args:
        context (str): The context for the story.
        style (str): The style of the story.
        story_title (str): The title of the story.
        query_dispatcher: An instance of the query dispatcher to send the query to ChatGPT.

    Returns:
        str: Generated filtered story in JSON format.
    """
    Logger.print_info("Generating filtered story with ChatGPT.")
    
    prompt = (
        f"You are a content filter that ensures text will pass OpenAI's content filters for DALL-E 3 image generation.\n\n"
        f"Filter and rewrite the following text to ensure it will pass content filters. The story should be titled '{story_title}' with the style of {style}. Here is the context to filter:\n\n"
        f"{context}\n\n"
        "Requirements:\n"
        "1. Make the story appropriate for all audiences\n"
        "2. Remove any sensitive or inappropriate content\n"
        "3. Rewrite sections with PII to only include publicly available information\n\n"
        "IMPORTANT: Return ONLY a JSON object in this exact format with no other text before or after:\n"
        "{\n"
        "  \"style\": \"<insert style here>\",\n"
        "  \"title\": \"<insert title here>\",\n"
        "  \"story\": \"<insert filtered story here>\"\n"
        "}"
    )

    try:
        response = query_dispatcher.sendQuery(prompt)
        
        # Parse the response to extract the filtered story
        response_json = json.loads(response)

        filtered_style = response_json["style"]
        filtered_title = response_json["title"]
        filtered_story = response_json["story"]

        if filtered_story == "No story generated":
            Logger.print_error("Failed to generate filtered story - error in response format. Response: " + response)

        Logger.print_info(f"Generated filtered story: {filtered_story}")
        return json.dumps({
            "style": filtered_style,
            "title": filtered_title,
            "story": filtered_story
        })
    except Exception as e:
        Logger.print_error(f"Error generating filtered story: {e}")
        return json.dumps({
            "style": style,
            "title": story_title,
            "story": "No story generated"
        })

def generate_movie_poster(filtered_story_json, style, story_title, query_dispatcher, retries=5, wait_time=60):
    try:
        filtered_story = json.loads(filtered_story_json)
    except json.JSONDecodeError:
        Logger.print_error("Filtered story is not in valid JSON format")
        return None
    
    filtered_context = filtered_story.get("story", "")
    if not filtered_context:
        Logger.print_error("Filtered story does not contain a story")
        return None

    prompt = f"Create a movie poster for the story titled '{story_title}' with the style of {style} and context: {filtered_context}."
    safety_retries = 3
    
    for safety_attempt in range(safety_retries):
        for attempt in range(retries):
            try:
                response = openai.Image.create(
                    model="dall-e-3",
                    prompt=prompt,
                    size="1024x1024",
                    quality="standard",
                    n=1
                )
                if response.data:
                    image_url = response['data'][0]['url']
                    filename = "/tmp/GANGLIA/ttv/movie_poster.png"
                    save_image_without_caption(image_url, filename)
                    return filename
                else:
                    Logger.print_error("No image was returned for the movie poster.")
                    return None
            except Exception as e:
                if 'Rate limit exceeded' in str(e):
                    Logger.print_warning(f"Rate limit exceeded. Retrying in {wait_time} seconds... (Attempt {attempt + 1} of {retries})")
                    time.sleep(wait_time)
                elif 'safety system' in str(e).lower():
                    # If we hit a safety rejection, try to filter the content further
                    Logger.print_warning(f"Safety system rejection. Attempting to filter content (Attempt {safety_attempt + 1} of {safety_retries})")
                    success, filtered_context = query_dispatcher.filter_content_for_dalle(filtered_context)
                    if success:
                        prompt = f"Create a movie poster for the story titled '{story_title}' with the style of {style} and context: {filtered_context}."
                        break  # Break the inner loop to try again with filtered content
                    else:
                        Logger.print_error("Failed to filter content")
                        return None
                else:
                    Logger.print_error(f"An error occurred while generating the movie poster: {e}")
                    return None
        else:
            # Inner loop completed without safety issues but hit rate limit
            continue
        # If we get here, we had a safety issue and filtered the content, so try again
        continue
    
    Logger.print_error(f"Failed to generate movie poster after {safety_retries} safety filtering attempts.")
    return None

def filter_text(sentence, context, style, query_dispatcher, retries=5, wait_time=60):
    Logger.print_debug(f"Filtering text to pass content filters: '{sentence}' with context '{context}' and style '{style}'")

    prompt = (
        f"Please filter this text to ensure it passes content filters for generating an image:\n\n"
        f"Sentence: {sentence}\n"
        f"Context: {context}\n"
        f"Style: {style}\n\n"
        "Please ensure that the filtered text does not contain any sensitive or inappropriate content.\n\n"
        "Please return ONLY a JSON object in this exact format (no other text):\n"
        "{\n"
        "  \"text\": \"<insert result here>\"\n"
        "}"
    )

    for attempt in range(retries):
        try:
            response = query_dispatcher.sendQuery(prompt)
            
            # Try to extract JSON from the response if it's not pure JSON
            try:
                # First try parsing the whole response
                response_json = json.loads(response)
            except json.JSONDecodeError:
                # If that fails, try to find JSON-like content within the response
                start = response.find('{')
                end = response.rfind('}') + 1
                if start >= 0 and end > start:
                    try:
                        response_json = json.loads(response[start:end])
                    except json.JSONDecodeError:
                        # If we still can't parse it, fall back to original sentence
                        return {"text": sentence}
                else:
                    # No JSON-like content found, fall back to original sentence
                    return {"text": sentence}

            filtered_sentence = response_json.get("text", sentence)  # Fallback to original sentence if key is not found
            if filtered_sentence != sentence:
                Logger.print_debug(f"Filtered sentence: {filtered_sentence}")
            return {"text": filtered_sentence}

        except (openai.error.RateLimitError, openai.error.APIError):
            Logger.print_warning(f"Rate limit or API error. Retrying in {wait_time} seconds... (Attempt {attempt + 1} of {retries})")
            time.sleep(wait_time)
        except requests.exceptions.RequestException as e:
            Logger.print_error(f"Network error: {e}")
            return {"text": sentence}

    Logger.print_error(f"Failed to filter text after {retries} attempts due to rate limiting.")
    return {"text": sentence}


def save_image_without_caption(image_url, filename):
    response = requests.get(image_url, timeout=30)  # 30 second timeout
    if response.status_code == 200:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'wb') as file:
            file.write(response.content)
    Logger.print_info(f"Movie poster saved to {filename}")
