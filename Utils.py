import xml.etree.ElementTree as ET


def parse_labelimg_xml(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    filename = root.find('filename').text
    size = root.find('size')

    objects = []
    for obj in root.findall('object'):
        name = obj.find('name').text
        bndbox = obj.find('bndbox')
        bbox = {
            'xmin': int(bndbox.find('xmin').text),
            'ymin': int(bndbox.find('ymin').text),
            'xmax': int(bndbox.find('xmax').text),
            'ymax': int(bndbox.find('ymax').text)
        }
        objects.append({
            'name': name,
            'bbox': bbox
        })

    return filename, objects


def main():
    xml_file = 'labelInfo/统计_工业产销总值及主要产品产量.xml'
    filename, objects = parse_labelimg_xml(xml_file)

    print(f'Parsed {filename}')
    for obj in objects:
        print(f"Object: {obj['name']}," f"BBox: {obj['bbox']}")


if __name__ == '__main__':
    main()
