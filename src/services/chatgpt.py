# Description: This file contains the functions 
# to interact with OpenAI's ChatGPT API

def get_vision_output(client, url):
    response = client.chat.completions.create(
    model="gpt-4-vision-preview",
    messages=[
        {
        "role": "user",
        "content": [
            {"type": "text", "text": "What’s in this image in high level?"},
            {
            "type": "image_url",
            "image_url": {
                "url": url,
                "detail": "high"
            },
            },
        ],
        }
    ],
    max_tokens=500,
    )
    content =response.choices[0].message.content
    return content



def generate_image_dalle(client, prompt, size="1024x1024", quality="hd", n=1):
    image_response = client.images.generate(
    model="dall-e-3",
    prompt=prompt,
    size=size,
    quality=quality,
    n=n,
    )

    image_url = image_response.data[0].url
    return image_url