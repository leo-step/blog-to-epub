import argparse
import pypub
import concurrent.futures
from utils import get_post_links, add_formatted_text_to_cover, fetch_title
from pypubpatch import *
import shutil
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, \
      QListWidget, QPushButton, QWidget, QMessageBox


def create_epub(url: str, title: str | None, cover: str | None, add_cover_text: bool):
    links = get_post_links(url)
    title = title or fetch_title(url)
    cover = cover or "./covers/red.png"

    os.makedirs("./output", exist_ok=True)

    def open_ui(links):
        class LinkManager(QMainWindow):
            def __init__(self):
                super().__init__()
                self.setWindowTitle("Select links for epub")
                self.result = []
                self.init_ui(links)

            def init_ui(self, links):
                # Main layout
                self.central_widget = QWidget()
                self.setCentralWidget(self.central_widget)
                layout = QVBoxLayout()

                # List widget to display links
                self.list_widget = QListWidget()
                self.list_widget.addItems(links)
                self.list_widget.setSelectionMode(QListWidget.MultiSelection)
                layout.addWidget(self.list_widget)

                # Buttons
                self.exclude_button = QPushButton("Exclude selected")
                self.exclude_button.clicked.connect(self.exclude_selected)
                layout.addWidget(self.exclude_button)

                self.reverse_button = QPushButton("Reverse order")
                self.reverse_button.clicked.connect(self.reverse_order)
                layout.addWidget(self.reverse_button)

                self.submit_button = QPushButton("Submit")
                self.submit_button.clicked.connect(self.submit)
                layout.addWidget(self.submit_button)

                # Set layout
                self.central_widget.setLayout(layout)

            def exclude_selected(self):
                for item in self.list_widget.selectedItems():
                    self.list_widget.takeItem(self.list_widget.row(item))

            def reverse_order(self):
                items = [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
                self.list_widget.clear()
                self.list_widget.addItems(reversed(items))

            def submit(self):
                self.result = [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
                if not self.result:
                    QMessageBox.critical(self, "Error", "No links left to process!")
                    return
                self.close()

        app = QApplication([])
        manager = LinkManager()
        manager.show()
        app.exec_()
        return manager.result

    links = open_ui(links)
    chapters = [None] * len(links)

    epub = pypub.Epub(title)
    epub.creator = url
    epub.publisher = "blog-to-epub"

    edited_title = title.replace(" ", "_")

    cover_output_path = f"./output/{edited_title}.png"
    if add_cover_text:
        add_formatted_text_to_cover(cover, title, url, cover_output_path)
    else:
        shutil.copyfile(cover, cover_output_path)
    epub.cover = os.path.abspath(cover_output_path)

    def create_chapter_from_url(link):
        try:
            return pypub.create_chapter_from_url(link)
        except: 
            return None

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(create_chapter_from_url, item): idx for idx, item in enumerate(links)}
        
        for future in concurrent.futures.as_completed(futures):
            idx = futures[future]
            chapters[idx] = future.result()

    for chapter in chapters:
        if chapter:
            epub.add_chapter(chapter)

    file_name = f"./output/{edited_title}.epub"
    epub.create(file_name)
    os.remove(cover_output_path)


def main():
    parser = argparse.ArgumentParser(
        description="Convert a blog into an epub for offline reading"
    )

    parser.add_argument(
        'url',
        type=str,
        help='Blog url (should be a page of links e.g. https://www.paulgraham.com/articles.html)'
    )

    parser.add_argument(
        '--title', '-t',
        type=str,
        default=None,
        help='Epub title (default: created automatically from blog name)'
    )

    parser.add_argument(
        '--cover', '-c',
        type=str,
        default=None,
        help='Cover image path, recommended size 400x600px (default: ./covers/red.png).'
    )

    parser.add_argument(
        '--no-add-cover-text',
        dest='add_cover_text',
        action='store_false',
        help='Flag to disable adding the epub title to the cover image.'
    )

    args = parser.parse_args()

    create_epub(args.url, args.title, args.cover, args.add_cover_text)


if __name__ == "__main__":
    main()
