""" Collection module
    Handles the datastructure of a collection, and saving and loading of
    metadata in a project folder
"""

import os
import json
import ntpath
import shutil
from typing import Optional
from dataclasses import dataclass, field

from dataclasses_json import dataclass_json


class CollectionManager():
    """ Summary
        -------
        Static class to manage the saving and loading of Collections.

        Methods
        -------
        load(path):
            loads a collection from a path.
        save(collection: Collection):
            saves a collection

        TODO
        ----
        - Make loading times faster
        - JSON format optimisation by minifying and aliasing the property
          names to take less space on disk.
    """

    AUTHORIZED_IMAGE_FORMATS = (".jpg", ".jpeg", ".png", ".webp", ".tiff")
    META_FILENAME = ".collection"

    @classmethod
    def load(self, path):
        """ Summary
            -------
            This function loads a collection from a path. If there is no
            collection here, create a new meta file

            Parameters
            ----------
            path: str
                path to the collection directory

            Returns
            -------
            collection: Collection
                the collection retrieved or created at the specified
                path

            Raises
            ------
            FileNotFoundError
                if the collection's work directory is not found

        """
                # check if the path given is valid
        if not os.listdir(path):
            raise FileNotFoundError
        


        # check if there is already a project file in this directory
        if CollectionManager.META_FILENAME in os.listdir(path):
            # if it's the case, load it.
            collection = self.__load_meta(path)
        else:
            # if it's not the case, create a new one and start with a
            # default collection
            self.__create_meta(path)
            # create a default collection
            collection = Collection(path, "Untitled Collection", list())

        # check the images in the directory and update the collection
        # and meta
        collection = self.__check_files(collection)
        self.__write_meta(collection)

        return collection

    @classmethod
    def save(self, collection):
        """ Summary
            -------
            This method saves a collection to disk.

            Parameters
            ----------
            collection: Collection
                the Collection object to save
        
        """
        self.__write_meta(collection)

    
    @classmethod
    def __load_meta(self, path):
        """ 
            Summary
            -------
            Deserializes the data from the meta file and updates the
            collection

            NOTE
            ----
            I'm sure there's a better way to do this...
        """
        with open(os.path.join(path, CollectionManager.META_FILENAME), "r") as meta:
            coll_json = meta.read()
            coll_dict = json.loads(coll_json)

        title = coll_dict["title"]
        collection = [
            # pylint says it's an error. It's not.
            CollectionImage.from_dict(item) for item in coll_dict["collection"]
        ]

        return Collection(path, title, collection)


    @classmethod
    def __check_files(self, collection):
        """ Runs through the files in the work directory and adds any
            image that is not yet in our collection.

            Returns
            -------
            checked_collection : Collection
                corrected collection (if new files are detected, they
                will be added to the collection, and the updated
                collection is returned)
        """
        # type safety check
        if not isinstance(collection, Collection):
            raise ValueError("collection must be of type Collection, not %s" 
                % type(collection)
            )

        for filename in os.listdir(collection.work_directory):
            # reject all files with the wrong extension (case
            # insensitive)
            if filename.lower().endswith(CollectionManager.AUTHORIZED_IMAGE_FORMATS):
                new_image = CollectionImage(filename)

                # this works since we overloaded the equal operator in
                # CollectionImage !
                if new_image not in collection.collection:
                    # add the new image
                    collection.collection.append(new_image)

        return collection


    @classmethod
    def __write_meta(self, collection):
        """ Serializes this collection and saves it in the project meta
            file in the work directory
        """
        # type safety check
        if not isinstance(collection, Collection):
            raise ValueError(
                "collection must be of type Collection, not %s" 
                % type(collection)
            )
        
        meta_file_path = os.path.join(
            collection.work_directory,
            CollectionManager.META_FILENAME
        )

        # create metadata file in the project directory
        with open(meta_file_path, "w") as meta_file:
            # pylint says it's an error. It's not.
            json_data = json.loads(collection.to_json())
            # format json file (temporary)
            formatted_json = json.dumps(json_data, indent=4)

            meta_file.write(formatted_json)


    @classmethod
    def __create_meta(self, path):
        path = os.path.join(path, CollectionManager.META_FILENAME)
        open(path, "a").close()


@dataclass_json
@dataclass
class Collection():
    """
        Summary
        -------
        Dataclass that represents a collection of images, that
        corresponds to a folder on the user's computer.

        Attributes
        ----------
        title : str, optional
            User entered name for the collection
        working_directory : str
            path to this collection's directory
        collection : list(CollectionImage), optional
            list of the images in the collection

        Methods
        -------
        get_collection()
            getter for the collection attribute
        set_collection(coll_list)
            setter for the collection attribute
    """
    work_directory : str
    title : Optional[str] = "Untitled Collection"
    collection: list = field(default_factory=list)

    def get_collection(self):
        """getter for the collection list"""
        return self.collection


    def set_collection(self, coll_list):
        """setter for the collection list"""
        self.collection = coll_list
        CollectionManager.save(self)
    

    def add_image(self, source):
        """ Summary
            -------
            Function to add an image to the collection

            Returns
            -------
            CollectionImage
                The image that was inserted in the collection
        
        """
        # cleaning the input if necessary
        source = str(source)
        if source.startswith("b'") and source.endswith("'"):
            source = source[2:-1]
        
        # get the file name, using ntpath
        file_name = ntpath.basename(source)

        # check that the file sent is of accepted format
        if not file_name.lower().endswith(
            CollectionManager.AUTHORIZED_IMAGE_FORMATS
        ):
            raise ValueError("Unauthorized file format for: %s" % file_name)

        # copy the file to the working directory
        # NOTE: should verify if the user is not dragging a file from
        # the working directory
        try:
            shutil.copyfile(source, os.path.join(self.work_directory, file_name))
        except shutil.SameFileError:
            raise shutil.SameFileError(file_name)
        
        new_image = CollectionImage(file_name)
        self.collection.append(new_image)
        CollectionManager.save(self)

        return new_image


    def get_absolute_path(self, collection_image):
        """ Summary
            -------
            Gives the absolute path to an image.

            Parameters
            ----------
            collection_image: CollectionImage
                an image
            
            Returns
            -------
            absolute_path: str
                absolute path to the image file
        """
        if not isinstance(collection_image, CollectionImage):
            raise ValueError("collection_image must be of type CollectionImage")

        return os.path.join(self.work_directory, collection_image.filename)



@dataclass_json
@dataclass
class CollectionImage():
    """
        Summary
        -------
        Dataclass that represents one image in a collection.
        It contains a pointer to the file on disk, and a set of
        metadata.

        Attributes
        ----------
        filename : str
            relative path to the file (eg. "image.png").
        title : str, optional
            title of the image
        artist : str, optional
            artist name
        year : str, optional
            production year (eg. "c. 1875")
        technique : str, optional
            technique (eg. "Oil on canvas")
        conservation_site : str, optional
            conservation site (eg. "Musée du Louvre, Paris")
        production_site : str, optional
            production site
        dimensions : str, optional
            dimensions of the work (eg. "300x200cm" or "20x30x25cm")

        Methods
        -------
        __eq__
            overloads the == operator

        NOTE
        ----
        - filename is deliberately a relative path, this prevents
          everything breaking in the case the directory is moved.
          To get the absolute path, use:
            os.path.join(collection.work_directory)
        - Date format to discuss.
    """

    filename :              str
    title :                 Optional[str] = None
    artist :                Optional[str] = None
    year :                  Optional[str] = None
    technique :             Optional[str] = None
    conservation_site :     Optional[str] = None
    production_site :       Optional[str] = None
    dimensions :            Optional[str] = None

    def to_reference(self):
        """ Formats the image metadata according to the guidelines at :
            https://www.unil.ch/files/live/sites/hart/files/shared
            /Espace_Etudiants/GPS_Guide_du_proseminaire.pdf

            NOTE
            ----
            Maybe allow for using different formattings ?
            This code assumes all fields are filled correctly
        """
        ref_string = "{artist_if_artist}{title}{production_site_if_no_artist}{date}{technique}{dimensions}{conservation_site}".format(
            artist_if_artist = self.artist + ", " if self.artist else "",
            title = self.title + ", ", # TODO: see about italics
            production_site_if_no_artist = self.production_site + ", " if not self.artist else "",
            date = self.year + ", ",
            technique = self.technique + ", ",
            dimensions = self.dimensions + ", ",
            conservation_site = self.conservation_site
        )

        return ref_string


    def __eq__(self, other):
        """ overloads the == operator so that two CollectionImages with
            the same filename are considered the same image.
        """
        return self.filename == other.filename


if __name__ == "__main__":
    coll = CollectionManager.load("testimages")
    print(coll)
