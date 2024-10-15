"""
    Basic Utility Methods needed
"""

from backgroundremover.bg import remove

def is_image_url(url):
    """
    Returns true if url is in valid form else false
    """
    if url.startswith("http://") or url.startswith("https://"):
        return True
    return False


DEFAULT_FORMATS = ["PNG"]


def is_format_match(image, formats=None):
    """
    Returns true if image format is matched in given formats
    else false
    """
    if not formats:
        formats = DEFAULT_FORMATS
    for f in formats:
        if image.format == f:
            return True
    return False


def cmp_tuples(t1, t2):
    """
    Returns true if two tuples contain same content else false
    """
    return len(t1) == len(t2) and set(t1) == set(t2)


def is_same_size(img1, img2):
    """
    Returns true if both images have same size else false
    """
    img1_size = img1.size
    img2_size = img2.size
    return cmp_tuples(img1_size, img2_size)

def remove_bg(src_img_path, out_img_path):
    model_choices = ["u2net", "u2net_human_seg", "u2netp"]
    f = open(src_img_path, "rb")
    data = f.read()
    img = remove(data, model_name=model_choices[0],
                 alpha_matting=True,
                 alpha_matting_foreground_threshold=240,
                 alpha_matting_background_threshold=10,
                 alpha_matting_erode_structure_size=10,
                 alpha_matting_base_size=1000)
    f.close()
    f = open(out_img_path, "wb")
    f.write(img)
    f.close()
