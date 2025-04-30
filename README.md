# Universal Content Download API

A FastAPI-based REST API for step-by-step extraction of movie/series download links from sites like vegamovies. 
This API is designed for easy frontend integration, providing a simple, consistent response structure.

---

## Overview

This API is intended for use by AI or frontend developers who want to build a UI that allows users to search for movies/series and retrieve download links in a guided, step-by-step fashion.

- **Stateless, chainable endpoints**: Each response tells you what to call next.
- **Unified response structure**: Easy for AI/automation to parse.
- **Error handling**: Uses HTTP status codes and a `detail` field.

---

## Base URL

```
http://localhost:8000
```

---

## Response Structure

All endpoints return:

```json
{
  "data": ...,
  "next_step": ...,
  "message": ...
}
```

- `data`: Main payload (list of results, buttons, or download links)
- `next_step`: Next endpoint/action (object or null)
- `message`: (Optional) User-friendly message

On errors, HTTP status codes and a `detail` field are returned.

---

## Endpoints

### 1. Search Content

**GET** `/search?query=...`

- **Params:**  
  - `query` (string): Movie or series name to search.

- **Response Example:**
    ```json
    {
      "data": [
        {
          "title": "Movie Title",
          "url": "https://...",
          "next_step": { "endpoint": "/extract", "params": { "url": "..." } }
        }
      ],
      "next_step": "Call 'next_step' for a result to continue."
    }
    ```

---

### 2. Extract Content Options

**GET** `/extract?url=...`

- **Params:**  
  - `url` (string): Direct URL to the movie/series page.

- **Response Example:**
    ```json
    {
      "data": [
        {
          "title": "Quality Group",
          "buttons": [
            {
              "text": "1080p",
              "link": "...",
              "next_step": { "endpoint": "/next-options", "params": { "url": "..." } }
            }
          ]
        }
      ],
      "next_step": "Call 'next_step' for a button to continue."
    }
    ```

---

### 3. Drill Down / Next Options

**GET** `/next-options?url=...`

- **Params:**  
  - `url` (string): URL from a previous button.

- **Response Example (more groups/buttons):**
    ```json
    {
      "data": [
        {
          "title": "Another Group",
          "buttons": [
            {
              "text": "Server 1",
              "link": "...",
              "next_step": { "endpoint": "/next-options", "params": { "url": "..." } }
            }
          ]
        }
      ],
      "next_step": "Call 'next_step' for a button to continue."
    }
    ```

- **Response Example (no more groups):**
    ```json
    {
      "data": null,
      "next_step": { "endpoint": "/resolve-downloads", "params": { "url": "..." } },
      "message": "No further download groups/buttons found. Use /resolve-downloads for direct download extraction."
    }
    ```

---

### 4. Resolve Final Download Links

**GET** `/resolve-downloads?url=...`

- **Params:**  
  - `url` (string): URL from a previous button or group.

- **Response Example (links found):**
    ```json
    {
      "data": [
        { "text": "Download [Server : 10Gbps]", "url": "..." }
      ],
      "next_step": null
    }
    ```

- **Response Example (no links):**
    ```json
    {
      "data": null,
      "next_step": null,
      "message": "No actual download links found."
    }
    ```

---

## Error Handling

- Errors return an HTTP status code (e.g., 404, 502) and a JSON body:
    ```json
    { "detail": "Error message" }
    ```

---

## How to Use for Frontend/AI

1. **Start with `/search?query=...`**
    - Present the user with a list of results from `data`.
    - For each result, use the `next_step` object to call the next endpoint.
2. **For Each Step:**
    - Display `data` as buttons or options.
    - On button click, follow the `next_step` for that button.
    - If `next_step` is an endpoint, call it with the provided params.
    - If `data` is a list of download links, present them for user download.
3. **Handle `message` and errors:**
    - Show `message` if present for user feedback.
    - Show error details if the API returns an error.

**AI/Automation Tips:**
- Always follow the `next_step` field to determine the next API call.
- If `data` is `null` and `next_step` is `null`, you have reached the end.
- Use the `message` field to provide context to the user.

---

## Development

- **Run the API:**  
  ```bash
  uvicorn main:app --reload
  ```
- **Interactive Docs:**  
  - [Swagger UI](http://localhost:8000/docs)
  - [Redoc](http://localhost:8000/redoc)

---

## License

MIT
