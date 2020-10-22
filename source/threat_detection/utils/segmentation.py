import os
from random import randint

import cv2
import numpy as np
import pandas as pd
import tqdm
from PIL import Image


def cropping(img_root, csv_path, output_path):
    """

    :param img_root: root to the images (positive included)
    :param csv_path: path to the csv generated from the xml annotations
    :param output_path: path to output the images
    """
    os.makedirs(output_path, exist_ok=True)
    df = pd.read_csv(csv_path)
    img_names = sorted(list(set(df['img_name'])))
    for name in tqdm.tqdm(img_names, 'Creating cropped objects'):
        objects = df.loc[df['img_name'] == name]
        image = cv2.imread(os.path.join(img_root, name))
        for index, row in objects.iterrows():
            os.makedirs(os.path.join(output_path, row['object_type']), exist_ok=True)

            crop_img = image[int(row['ymin']):int(row['ymax']), int(row['xmin']):int(row['xmax'])]
            im_name = name.split('.')[0] + '_' + str(index) + '.jpg'
            cv2.imwrite(os.path.join(output_path, row['object_type'], im_name), crop_img)


# TODO: Fine tune segmentation
def segmentation(img, low_hsv, high_hsv, negate):
    """
    This is just a proof of concept function for the segmentation, should be refined
    Segmentation type based on: https://medium.com/srm-mic/color-segmentation-using-opencv-93efa7ac93e2
    :param low_hsv: segmentation rule based: specifying color boundaries
    :param img: image that needs to be segmented
    :param high_hsv: segmentation rule based: specifying color boundaries
    :param negate: specify if return the negate of the mask
    """
    blur = cv2.blur(np.array(img), (5, 5))
    blur0 = cv2.medianBlur(blur, 5)
    blur1 = cv2.GaussianBlur(blur0, (5, 5), 0)
    blur2 = cv2.bilateralFilter(blur1, 9, 75, 75)
    hsv = cv2.cvtColor(blur2, cv2.COLOR_BGR2HSV)

    mask = cv2.inRange(hsv, low_hsv, high_hsv)
    if negate:
        mask = ~mask
    result = cv2.bitwise_and(np.array(img), np.array(img), mask=mask)
    return result, mask


def remove_small(base_dir, object_type, min_dim):
    """
    Remove the unnecessarily small images
    :param min_dim: remove images that are smaller than this dimension
    :param base_dir: Base dir of the segmentation, like the cropped "Gun" folder
    :param object_type: Specifying the type of the object
    """
    images = os.listdir(os.path.join(base_dir, object_type))
    for image in tqdm.tqdm(images, 'Removing small images'):
        if image.endswith('.png') or image.endswith('.jpg'):
            img_path = os.path.join(base_dir, object_type, image)
            img = cv2.imread(img_path)
            if min_dim[0] > img.shape[0] or min_dim[1] > img.shape[1]:
                os.remove(img_path)


def rescale(img, scale):
    """

    :param img: The image of the object that needs to be segmented
    :param scale: the scaling ratio between the height and width of the negative image and the object
    :return:
    """
    ratio = scale[1] / scale[0]
    resize = randint(1, int(np.max(scale) / 2))
    img = img.resize((round(img.size[0] * (resize/ratio)), round(img.size[1] * resize)))
    return img


def area_of_interest(base_img, inv_mask, obj_width, obj_height):
    """
    Selects the area of interest from the negative image, basically the background for the segmented object
    :param base_img: Negative image
    :param inv_mask: negated mask of the object segmentation
    :param obj_width: width of the object
    :param obj_height: height of the object
    :return:
    """
    # Select the area to insert the segmented gun with a negative mask, and returns its surroundings
    aoi = cv2.bitwise_and(np.array(base_img[250:250 + obj_width, 250:250 + obj_height]),
                          np.array(base_img[250:250 + obj_width, 250:250 + obj_height]),
                          mask=inv_mask)
    return aoi


def get_avg_size_ratios(base_dir, object_type, path_to_negatives):
    """
    Calculate the object ratios to the negative images
    :param base_dir: Base dir of the segmentation, like the cropped "Gun" folder
    :param object_type: Specifying the type of the object
    :param path_to_negatives: path to the negative images that need augmentation
    :return:
    """
    if not os.path.exists(os.path.join(base_dir, object_type, 'size_scale.txt')):
        avg_size_mistmatch = np.array([0, 0]).astype(float)
        images = os.listdir(os.path.join(base_dir, object_type))
        negatives = os.listdir(path_to_negatives)
        for image in tqdm.tqdm(images, 'Avg scale'):
            img_path = os.path.join(base_dir, object_type, image)
            rand_path = os.path.join(path_to_negatives, negatives[randint(0, len(negatives))])
            random_negative = Image.open(rand_path).convert('RGB')
            threat_obj = Image.open(img_path).convert('RGB')
            avg_size_mistmatch += np.array(np.array(random_negative.size) / np.array(threat_obj.size)).astype(float)
        np.savetxt(os.path.join(base_dir, object_type, 'size_scale.txt'), avg_size_mistmatch / len(images))
        return avg_size_mistmatch / len(images)
    return np.loadtxt(os.path.join(base_dir, object_type, 'size_scale.txt'))


def run_segmentation(base_dir, object_type, path_to_negatives):
    """
    Run the different segmentations and compare them
    :param path_to_negatives: path to the negative images that need augmentation
    :param base_dir: Base dir of the segmentation, like the cropped "Gun" folder
    :param object_type: Specifying the type of the object
    """
    images = os.listdir(os.path.join(base_dir, object_type))
    negatives = os.listdir(path_to_negatives)

    # TODO: Find the boundaries of the luggage
    for image in images:
        if image.endswith('.png') or image.endswith('.jpg'):
            img_path = os.path.join(base_dir, object_type, image)
            rand_path = os.path.join(path_to_negatives, negatives[randint(0, len(negatives))])
            random_negative = Image.open(rand_path).convert('RGB')
            random_negative_cv = np.array(random_negative)
            random_negative_cv = random_negative_cv[:, :, ::-1].copy()

            threat_obj = Image.open(img_path).convert('RGB')
            # Random resize
            threat_obj = rescale(threat_obj, np.loadtxt(os.path.join(base_dir, object_type, 'size_scale.txt')))
            # Random rotation
            threat_obj = threat_obj.rotate(randint(0, 360), expand=True)
            threat_obj_cv = np.array(threat_obj)
            threat_obj_cv = threat_obj_cv[:, :, ::-1].copy()
            cv2.imshow('R', np.array(threat_obj_cv))
            cv2.waitKey(0)
            cv2.destroyAllWindows()
            # TODO: Handle bounding box and annotation generation
            low_blue = np.array([55, 0, 0])
            high_blue = np.array([118, 255, 255])
            result, mask = segmentation(threat_obj_cv, low_blue, high_blue, False)
            aoi_background = area_of_interest(random_negative_cv, ~mask, result.shape[0], result.shape[1])

            # TODO: FIND BETTER POSITIONING
            # Add together to object and the surrounding from the other image and overwrite the part of the negative img
            random_negative_cv[250:250 + result.shape[0], 250:250 + result.shape[1]] = (aoi_background + result)
            cv2.imshow('F', np.array(random_negative_cv))
            cv2.waitKey(0)
            cv2.destroyAllWindows()


root_path_pos = 'Datasets/SIXRay/tar/Positive'
root_path_neg = '/Datasets/SIXRay/tar/Negative_reduced'
path_to_csv = '/Datasets/SIXRay/gt_data.csv'
out_dir = '/Datasets/SIXRay/output'

# 1. Crops out the area of interest from the positive images, like guns, knives, etc..
cropping(root_path_pos, path_to_csv, out_dir)
# 2. Get average size scale between obj and negative images

avg_scale = get_avg_size_ratios(out_dir, 'Gun', root_path_neg)

# 2. Removes the small objects, that are useless for augmentation
remove_small(out_dir, 'Gun', (99, 50))

# 3. Runs the segmentation
run_segmentation(out_dir, 'Gun', root_path_neg)
