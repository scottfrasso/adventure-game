from pydantic import BaseModel
import xmltodict

class BaseModelWithXML(BaseModel):
    def to_xml(self) -> str:
        def convert_list_to_dict(d):
            for key, value in d.items():
                if isinstance(value, list):
                    d[key] = {key[:-1]: value}  # Use singular form of key as XML tag
                elif isinstance(value, dict):
                    convert_list_to_dict(value)

        # Convert the model to a dictionary
        model_dict = {self.__class__.__name__: self.dict()}
        
        # Convert lists in the dictionary to a format that xmltodict can handle as single tags
        convert_list_to_dict(model_dict[self.__class__.__name__])
        
        # Convert the dictionary to an XML string without the XML declaration
        xml_str = xmltodict.unparse(model_dict, full_document=False, pretty=True)
        return xml_str
