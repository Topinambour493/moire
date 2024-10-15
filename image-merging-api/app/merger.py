#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
    This module has a class Merger which takes two urls of images
    and it returns the merged image .And , also contains a utility
    function get_image , return an Image object by downloading a
    image of given url.
"""

import base64
import logging
import os
from hashlib import md5
from io import BytesIO, StringIO
from uuid import uuid4
import requests
from PIL import Image
from requests.exceptions import RequestException, Timeout

from .utils import is_format_match, is_image_url, is_same_size

logger = logging.getLogger(__name__)


class Error(Exception):
    """
    Exception raised for errors in the module.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message=""):
        self.message = message

    def __str__(self):
        return repr(self.message)


class UrlError(Error):
    """
    Exception raised for invalid image url.
    """

    pass


class FormatError(Error):
    """
    Exception raised for invalid image format.
    """

    pass


class SizeError(Error):
    """
    Exception raised for image sizes not match.
    """

    pass


DEFAULT_REQUEST_TIMEOUT = 30
DEFAULT_REQUEST_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 ("
    "KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36"
)
DEFAULT_REQUEST_RETRY = 5


def get_image_by_url(url):
    """
    Return PIL Image object after downloading the image via Url

    Parameters:
        url -- an url of png image

    Returns:
         an Image object

    Raises:
        RequestException -- if there is problem in connection
    """
    retry_count = 0
    while True:
        try:
            req_headers = {"User-Agent": DEFAULT_REQUEST_UA}
            r = requests.get(
                url, headers=req_headers, stream=True, timeout=DEFAULT_REQUEST_TIMEOUT
            )
            image_data = r.content
            if isinstance(image_data, bytes):
                image_data = BytesIO(image_data)
            else:
                image_data = StringIO(image_data)

            im = Image.open(image_data)
            return im
        except Timeout as e:
            if retry_count <= DEFAULT_REQUEST_RETRY:
                continue
            else:
                raise e
        except Exception as e:
            logging.exception(e)
            raise RequestException(e)


class Merger:
    """
    Merge two png images (i.e background and foreground)

    Attributes:
        foreground_url -- url of foreground image
        background_url -- url of background image
        output_image -- Image object contains output image
        output_image_name -- name of output_image

    Methods:
        merge_images -- merge foreground and background images
        get_output_image -- gets the output_image in different types
        save_output_image_to_directory -- save output_image to directory
    """

    def __init__(self, urls, foreground_color=None, background_color=None):
        """
        Sets the foreground_url and background_url
        """
        if background_color is None:
            background_color = [0, 255, 0]
        background_color.append(255)
        if foreground_color is None:
            foreground_color = [255, 0, 255]
        self.background_color = tuple(background_color)
        self.foreground_color = tuple(foreground_color)
        self.urls = urls
        self.output_image = None
        self.output_image_name = None

    def merge_images(self):
        """
        Merge foreground_url and background_url and Sets
        output_image

        Raises:
            Error -- if any error occurs
        """
        try:
            for i in range(len(self.urls)):
                # if not is_image_url(self.urls[i]):
                #     raise UrlError("`url[" + str(i) + "]` is not valid url")
                self.urls[i] = Image.open(self.urls[i])
                self.urls[i] = self.urls[i].convert('RGBA')
                # if not is_format_match(self.urls[i]):
                #     raise FormatError("`url[" + str(i) + "]` is not of PNG format")
                if not is_same_size(self.urls[i], self.urls[0]):
                    raise SizeError("images are of different size")
            size = self.urls[0].size
            background = Image.new("RGBA", size, self.background_color)
            size_box = (11, size[1])
            transparent = Image.new("L", size_box, 0)
            region = Image.merge("RGBA", (transparent, transparent, transparent, transparent))
            for i in range(3):
                r, g, b, a = self.urls[i].split()
                new_r = Image.new("L", size, self.foreground_color[0])
                new_g = Image.new("L", size, self.foreground_color[1])
                new_b = Image.new("L", size, self.foreground_color[2])
                self.urls[i] = Image.merge("RGBA", (new_r, new_g, new_b, a))
                for j in range(i, size[0], 15):
                    box = (j, 0, 11 + j, size[1])
                    self.urls[i].paste(region, box)
            self.output_image = Image.alpha_composite(background, self.urls[0])
            for i in range(1, len(self.urls)):
                self.output_image = Image.alpha_composite(self.output_image, self.urls[i])
            self.save_output_image_to_directory()

        except UrlError:
            raise Error("Not a valid image url")
        except FormatError:
            raise Error("Format not supported")
        except RequestException:
            raise Error("Images not found. Please check image urls")
        except SizeError:
            raise Error("Not same size images")
        except Exception as e:
            logger.exception(e)
            raise Error("Internal Error. Please Try Again")

    def get_output_image(self, o_type="Image"):
        """
        Gets the output(i.e merged) image

        Attributes:
            o_type -- tells the return type of output_image
        """
        o_type = o_type.lower()
        if o_type == "name":
            return self.output_image_name
        if o_type == "image":
            return self.output_image
        elif o_type == "base64":
            image_data = self.get_output_image(o_type="String")
            encoded_image_data = base64.b64encode(image_data)
            return encoded_image_data.decode()
        elif o_type == "string":
            img_io = BytesIO()
            self.output_image.save(img_io, "PNG")
            img_io.seek(0)
            return img_io.getvalue()

    def save_output_image_to_directory(self):
        """
        Saves the output_image to images/ directory
        """
        curr_directory = os.path.dirname(os.path.abspath(__file__))
        images_dir = curr_directory + "/images/"
        if not os.path.exists(images_dir):
            os.makedirs(images_dir)
        self.output_image_name = md5(str(uuid4()).encode()).hexdigest() + ".png"
        image_file_name = images_dir + self.output_image_name
        self.output_image.save(image_file_name)
        logger.info("Image file saved locally : %s", image_file_name)


