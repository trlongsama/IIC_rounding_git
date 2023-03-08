import streamlit as st
from bs4 import BeautifulSoup
import decimal
import os
import xmlformatter
import config
import math
import numpy as np
import pandas as pd


file_path = 'INV-271267_example.xml'
save_folder_path = config.LOCAL_STORAGE
formatter = xmlformatter.Formatter(indent="1", indent_char="\t", encoding_output="utf-8", preserve=["literal"])

def save_temp_file(file_name: str, bytes_info: bytes):
    file_path = os.path.join(save_folder_path, file_name)
    with open(file_path, 'wb') as file:
        file.write(bytes_info)
    return os.path.abspath(file_path) 

def parse_xml(file_path, option):
    global formatter
    filename = os.path.basename(file_path)
    filename_wo_ext = filename.split('.')[0]
    with open(file_path, 'r') as file:
        xml = file.read()

    # parse the XML with BeautifulSoup
    soup = BeautifulSoup(xml, 'xml')

    # find all fee elements
    fee_summary = soup.find_all('fee')

    def create_custom_tag(name, value):
        custom_tag = soup.new_tag(name)
        custom_tag.string = str(value)
        return custom_tag

    status_lst = []
    for _, item in enumerate(fee_summary):
        unit = item.units.text
        unit_val = decimal.Decimal(unit.strip('0'))
        unit_float = float(unit)
        rate = item.rate.text
        rate_val = decimal.Decimal(rate.strip('0'))
        rate_float = float(rate)
        amount = item.total_amount.text
        amount_val = decimal.Decimal(amount.strip('0'))
        amount_float = float(amount)
        if unit_val.as_tuple().exponent>=-2 and rate_val.as_tuple().exponent>=-2 and amount_val.as_tuple().exponent>=-2:
            # keep original
            adjusted_unit = unit_float
            item.units.replace_with(create_custom_tag('units', adjusted_unit))

            adjusted_amount = amount_float
            item.total_amount.replace_with(create_custom_tag('total_amount', adjusted_amount))

            adjusted_rate = rate_float
            item.rate.replace_with(create_custom_tag('rate', adjusted_rate))
            status_lst.append([item.charge_date.text, 'unchanged', unit, rate, amount, np.nan, np.nan, np.nan])
        else:
            # adjusted
            if option == 'Amount':
                if unit_val.as_tuple().exponent < -2:
                    adjusted_unit = round(math.floor(unit_float * 100) / 100 + 0.01, 2)
                else:
                    adjusted_unit = round(unit_float, 2)
                item.units.replace_with(create_custom_tag('units', adjusted_unit))

                adjusted_amount = round(amount_float, 2)
                item.total_amount.replace_with(create_custom_tag('total_amount', adjusted_amount))

                adjusted_rate = round(adjusted_amount/adjusted_unit, 2)
                item.rate.replace_with(create_custom_tag('rate', adjusted_rate))
                status_lst.append([item.charge_date.text, 'adjusted', unit, rate, amount, str(adjusted_unit), str(adjusted_rate), str(adjusted_amount)])
                #print("item date {} unit {} rate {} amount {}, adjusted to {}, {}, {}".format(item.charge_date.text, unit,
                #                                            rate, amount, adjusted_unit, adjusted_rate, adjusted_amount))
            elif option == 'Rate':
                if amount_val.as_tuple().exponent < -2:
                    adjusted_amount = round(math.floor(amount_float * 100) / 100 + 0.01, 2)
                else:
                    adjusted_amount = round(amount_float, 2)

                adjusted_rate = round(rate_float, 2)
                item.rate.replace_with(create_custom_tag('rate', adjusted_rate))

                adjusted_unit = round(adjusted_amount/adjusted_rate, 2)
                item.units.replace_with(create_custom_tag('units', adjusted_unit))

            status_lst.append([item.charge_date.text, 'adjusted', unit, rate, amount, str(adjusted_unit), str(adjusted_rate), str(adjusted_amount)])
    #print(status_lst)
    log_df = pd.DataFrame(status_lst, columns=['Date', 'Status', 'unit','rate', 'amount','adjusted_unit','adjusted_rate', 'adjusted_amount'])
    new_filename = f'{filename_wo_ext}_UPDATED.xml'
    xml_bytes_string = formatter.format_string(str(soup))
    return save_temp_file(new_filename, xml_bytes_string), log_df

option = st.selectbox(
    'Select fixed field for not rounding up',
    ('Amount', 'Rate'))


with st.form(key="Form :", clear_on_submit = True):
    uploaded_file = st.file_uploader(label = "Upload file", type=["xml"])
    Submit = st.form_submit_button(label='Submit')

if not os.path.exists(save_folder_path):
    os.makedirs(save_folder_path)

if Submit:
    file_name = uploaded_file.name
    #print("processing {}".format(file_name))
    file_bytes = uploaded_file.read()
    is_upload_success = False
    try:
        file_path = save_temp_file(file_name, file_bytes)
        is_upload_success = True
    except Exception as e:
        st.error(f'Failed to save file to {os.path.abspath(save_folder_path)} due to {e}')
    if is_upload_success:
        st.success(f'Uploaded file {file_name} successfully.')
        try:
            save_file_path, log_df = parse_xml(file_path, option)
            st.success(f'Generated xml successfully.')
            with open(save_file_path, "rb") as fp:
                file_name = os.path.basename(save_file_path)
                st.download_button('Download XML', fp, file_name, mime="application/xml")
                st.dataframe(log_df)
        except Exception as e:
            st.error("Generate xml failed: {}".format(e))

filelist = [f for f in os.listdir(save_folder_path)]
for f in filelist:
    os.remove(os.path.join(save_folder_path, f))
        
