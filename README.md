# blog-to-epub

## Overview

This program converts a collection of blog posts from a webpage into an epub file for offline reading. You can customize the epub's title, cover image, and more. It provides a simple UI for managing links, excluding unwanted ones, and reversing their order. The tool is perfect for saving your favorite blogs in a clean and portable format.
<br />
<br />
<img width="1060" alt="Screenshot 2024-11-16 at 4 08 56 PM" src="https://github.com/user-attachments/assets/fff01733-b33c-442a-8212-ec39765518f3">

## Features

- Automatically detects and extracts blog post links from a webpage.
- Provides a UI to exclude or reorder links before conversion.
- Adds a custom or default cover image with optional text overlays.
- Multithreaded fetching of blog posts for fast conversion.
- Cleans and validates HTML content to ensure proper epub formatting.

---

## Installation

### Prerequisites
- Python 3.8 or higher
- pip

### Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/leo-step/blog-to-epub.git
   cd blog-to-epub
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## Usage

### Command-Line Usage

Run the script with the following command:
```bash
python blogtoepub.py <URL> [options]
```

#### Positional Argument:
- `URL`: The URL of the blog page containing links to articles.

#### Optional Arguments:
- `--title, -t`: Custom title for the epub (default: derived from the blog's name).
- `--cover, -c`: Path to a custom cover image (default: `./covers/red.png`).
- `--no-add-cover-text`: Disable adding title and URL text to the cover image.

#### Example:
```bash
python blogtoepub.py https://example.com/blog -t "My Blog Collection" --cover ./covers/custom.png
```

### Interactive Link Management
When the program fetches links from the provided URL, it opens a UI where you can:
- Exclude selected links.
- Reverse the order of links.
- Submit your final selection.

---

## Algorithms and Key Features

### Link Detection Algorithm
To extract blog post links from a page, we employ the **largest repeating subtree** algorithm:

1. **Node Representation**:
   Each HTML element is represented as a `Node`, which includes:
   - The element's tag and attributes.
   - A hash representing its structure.
   - A list of its children.

2. **Subtree Hashing**:
   Each node computes a hash that includes:
   - Its tag name.
   - A sorted list of its attributes.
   - The hashes of its child nodes.

3. **Subtree Size Analysis**:
   Subtrees are counted based on their hashes. The largest repeating subtree typically corresponds to the main content of the page, such as blog post links.

4. **Filtering Links**:
   Links within the detected subtree are cleaned and filtered to remove duplicates, images, and invalid URLs.

### UI for Link Selection
The program uses PyQt5 to provide an interactive UI:
- **Exclude Selected**: Removes unwanted links.
- **Reverse Order**: Changes the order of links for custom sequencing.
- **Submit**: Finalizes your selection.

### Cover Customization
Covers are generated using PIL with optional text overlays. The program automatically wraps and fits the text into the image, ensuring a professional appearance.

---

## Output
- epub files are saved in the `output/` directory.
- The file name is derived from the title (spaces replaced with underscores).
