import pandas as pd
import tkinter as tk
from tkinter import filedialog
import pubchempy as pcp
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def fetch_mol_info(name):
    compound = pcp.get_compounds(name, 'name')
    if compound:
        compound = compound[0]
        smiles = compound.isomeric_smiles
        print(f"SMILES for {name}: {smiles}")

        compounds_by_smiles = pcp.get_compounds(smiles, 'smiles')
        if compounds_by_smiles:
            cid = compounds_by_smiles[0].cid
            print(f"CID for {name}: {cid}")
            hazard_info = fetch_h_info(cid)
            print(f"Hazard information: {hazard_info}")
            return hazard_info
    return None

def fetch_h_info(cid, retries=3):
    url = f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}#section=GHS-Classification"
    options = Options()
    options.headless = True
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    hazard_info = {'pictograms': []}

    for attempt in range(retries):
        try:
            driver.get(url)
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "GHS-Classification")))
            ghs_section = driver.find_element(By.ID, "GHS-Classification")
            pictograms = ghs_section.find_elements(By.CLASS_NAME, 'captioned')
            hazard_info['pictograms'] = [pic.get_attribute('data-caption').strip().lower() for pic in pictograms] if pictograms else []
            break
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
    driver.quit()
    return hazard_info

def cat_pict(pictograms):
    return {pic: 1 for pic in pictograms}

def main():
    csv_file = select_csv()
    if not csv_file:
        print("No file selected.")
        return

    df = pd.read_csv(csv_file)
    if 'Mol' not in df.columns:
        print("CSV must contain a 'Mol' column.")
        return

    results, all_pictograms = [], set()

    for _, row in df.iterrows():
        name = row['Mol']
        hazard_info = fetch_mol_info(name)
        
        result_row = {'Mol': name}
        
        if hazard_info is None:
            result_row['NA'] = 1
        else:
            pictogram_data = cat_pict(hazard_info['pictograms'])
            result_row.update(pictogram_data)
            all_pictograms.update(hazard_info['pictograms'])

        results.append(result_row)

    final_columns = ['Mol'] + list(all_pictograms)
    result_df = pd.DataFrame(results, columns=final_columns)

    output_file = csv_file.replace(".csv", "_output.csv")
    result_df.to_csv(output_file, index=False)
    print(f"Results saved: {output_file}")

def select_csv():
    root = tk.Tk()
    root.withdraw()
    return filedialog.askopenfilename(title="Select CSV", filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])

if __name__ == "__main__":
    main()
