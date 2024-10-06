import re
import os
import json
from warning_manager import WarningManager

#! THIS HAS TO BE IMPORTED OR IT WILL NOT SEE THE STRATEGY FACTORY AND THUS YOU WILL GET AN ERROR
import AttributeExtractionStrategies
from strategy_factory import StrategyFactory
from enums import AttributeTypes

# TODO: make documentation on the class and it's methods

"""
This script contains a class that has various utility methods that will be used for many purposes throughout the project
"""


class Utilities:
    MAX_FILENAME_LENGTH = 255

    def __init__(
        self, *, strategy_factory: StrategyFactory, warning_manager: WarningManager
    ):
        self.strategy_factory = strategy_factory
        self.warning_manager = warning_manager

    def get_attributes(self, entry_text, attributes):
        """
        Extracts specified attributes from the article entry and returns them in a dictionary.
        It also warns about missing or invalid attributes.

        Parameters:
            entry_text (str): The text of the article entry.
            attributes (list of str): A list of attribute names to extract from the entry, e.g., ["title", "author"].

        Returns:
            dict: A dictionary where keys are attribute names and values are tuples.
                  Each tuple contains a boolean indicating success or failure of extraction,
                  and the extracted attribute value or None.

        Raises:
            ValueError: If an attribute not defined in `self.attribute_patterns` is requested.
        """
        attribute_results = {}
        for attribute in attributes:
            extraction_strategy = StrategyFactory.get_strategy(
                attribute, self.warning_manager
            )
            attribute_results[attribute] = extraction_strategy.extract_attribute(
                entry_text
            )
        return attribute_results

    def get_tc_list(self, entry_text):
        """
        Extracts the list of topic categories from the entry text.

        Args:
            entry_text (str): The text of the entry.

        Returns:
            list: A list of topic categories.
        """
        tc_list = []

        for line in entry_text.split("\n"):
            if line.startswith("TC"):
                tc_list.append(line[3:])

        return tc_list

    def sanitize_filename(self, text, max_length=MAX_FILENAME_LENGTH):
        """
        Sanitizes a string for use as part of a file name.

        Args:
            text (str): The text to sanitize.
            max_length (int): The maximum allowed length of the sanitized string. If nothing is provided defaults to MAX_FILENAME_LENGTH

        Returns:
            str: A sanitized string safe for use in a file name.
        """

        # Remove any potential HTML tags
        text = re.sub("<[^>]+>", "", text)

        # Replace invalid filename characters with underscores
        invalid_chars = r'[<>:"/\\|?*\n]+'
        sanitized = re.compile(invalid_chars).sub("_", text)

        # Truncate to avoid excessively long file names
        return sanitized[:max_length]

    def get_article_title(self, entry_text):
        """
        Extracts the title of the article from the entry text.
        """
        return self.attribute_patterns["title"].extract_attribute(entry_text)

    def get_file_name(self, author, title):
        """
        Constructs a filename using the first author's name and the title of an entry.

        Parameters:
            author (str): The author(s) of the entry.
            title (str): The title of the entry.

        Returns:
            str: A sanitized and formatted filename.
        """
        first_author = author[0].strip()

        # sanitize and truncate the first authors name and title
        sanitized_author = self.sanitize_filename(first_author)
        sanitized_title = self.sanitize_filename(title)

        # construct file name
        file_name = f"Author:{sanitized_author}_Title:{sanitized_title}.txt"

        # return formatted file name
        return file_name[:255]

    def get_output_dir(self, path=None):
        """
        Ensures the output directory exists, creating it if necessary.

        Parameters:
            path (str, optional): The path to the output directory. Defaults to the current working directory if None.

        Returns:
            str: The path to the output directory.
        """
        # Use current working directory if no path is provided
        if path is None:
            return os.getcwd()

        # Create the directory if it doesn't exist
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        return path

    def splitter(self, *, path_to_file, output_dir):
        """
        Splits a document into individual entries based on a specified delimiter.

        Parameters:
            path_to_file (str): The path to the the document to be split

        Returns:
            list: A list of strings, each representing an individual entry from the document.
        """
        # Read entire document into memory
        with open(path_to_file, "r", encoding="utf-8") as file:
            file_content = file.read()

        # Split the document into entries based on the end record delimiter
        splits = self.end_record_pattern.split(file_content)

        # filter out any empty strings that may result from splitting
        # re-add delimiter for completeness if needed
        splits = [split + "DA 2024-02-08\nER" for split in splits if split.strip()]
        return splits

    def crossref_file_splitter(self, *, path_to_file, output_dir):
        output_dir = self.get_output_dir(output_dir)
        
        with open(path_to_file, "r") as f:
            data = json.load(f)
        crossref_filename_suffix = "_crossref_item.json"
        
        for i, item in enumerate(data):
            file_name = f"{i}{crossref_filename_suffix}"
            full_file_path = os.path.join(output_dir, file_name)
            with open(full_file_path, "w") as f:
                json.dump(item, f, indent=4)
        
        files = os.listdir(output_dir)
        return files

    def make_files(
        self, *, path_to_file: str, output_dir: str, crossref_bool: bool = False
    ):
        """
        Splits a document into individual entries and creates a separate file for each entry in the specified output directory.

        Parameters:
            path_to_file (str): The path to the full text file containing all metadata for the entries.
            output_dir (str): The path to the directory where the individual entry files should be saved.

        Returns:
            file_paths: A dictionary where each key is the number of the entry (starting from 1) and each value is the path to the corresponding file.

        This method first splits the document into individual entries using the `splitter` method.
        It then iterates over each entry, extracts the necessary attributes to form a filename,
        ensures the output directory exists, and writes each entry's content to a new file in the output directory.
        Then returns the file_paths dictionary to make referencing any specific document later easier
        """
        if crossref_bool:
            return self.crossref_file_splitter(
                path_to_file=path_to_file,
                output_dir=output_dir
            )

        splits = self.splitter(path_to_file=path_to_file, output_dir=output_dir)

        # dictionary to keep track of created files and their paths
        file_paths = {}

        for index, split in enumerate(splits, start=1):
            # Extract attributes to form filename
            attributes = self.get_attributes(
                split, [AttributeTypes.AUTHOR, AttributeTypes.TITLE]
            )
            author = (
                attributes[AttributeTypes.AUTHOR][1]
                if attributes[AttributeTypes.AUTHOR][0]
                else "Unknown"
            )
            title = (
                attributes[AttributeTypes.TITLE][1]
                if attributes[AttributeTypes.TITLE][0]
                else "Unkown"
            )

            # Construct file name
            file_name = self.get_file_name(author, title)

            # Ensure output directory exists
            save_in_dir = self.get_output_dir(output_dir)

            # Construct full path for new file
            path = os.path.join(save_in_dir, file_name)

            # Check if file already exists to avoid duplicates/overwriting
            if not os.path.exists(path):
                # Write the entry's contents to the new file
                with open(path, "w") as new_file:
                    new_file.write(split)

                # Track the created file
                file_paths[index] = path
            else:
                self.warning_manager.log_warning(
                    "File Creation", f"File {path} already exists. Skipping."
                )
        return file_paths
