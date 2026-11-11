"""Common medicines in India, generic name + usual strength, for typing help in "Add medicine".
Brands are many and change; the generic plus strength is what the label and the doctor's handwriting share."""
COMMON = """Paracetamol 500 mg|Paracetamol 650 mg|Ibuprofen 400 mg|Aceclofenac 100 mg|Diclofenac 50 mg|Aspirin 75 mg|Aspirin 150 mg|Clopidogrel 75 mg|
Atorvastatin 10 mg|Atorvastatin 20 mg|Atorvastatin 40 mg|Rosuvastatin 5 mg|Rosuvastatin 10 mg|Rosuvastatin 20 mg|Fenofibrate 160 mg|Ezetimibe 10 mg|
Metformin 500 mg|Metformin 850 mg|Metformin 1000 mg|Metformin SR 500 mg|Glimepiride 1 mg|Glimepiride 2 mg|Gliclazide 80 mg|Gliclazide MR 60 mg|
Sitagliptin 100 mg|Sitagliptin + Metformin 50/500 mg|Vildagliptin 50 mg|Vildagliptin + Metformin 50/500 mg|Teneligliptin 20 mg|Linagliptin 5 mg|
Dapagliflozin 10 mg|Empagliflozin 10 mg|Empagliflozin 25 mg|Pioglitazone 15 mg|Voglibose 0.2 mg|Acarbose 50 mg|Insulin Glargine 100 IU/mL|
Insulin Aspart 100 IU/mL|Insulin Human Mixtard 30/70|Telmisartan 40 mg|Telmisartan 80 mg|Telmisartan + Hydrochlorothiazide 40/12.5 mg|
Telmisartan + Amlodipine 40/5 mg|Losartan 50 mg|Olmesartan 20 mg|Amlodipine 5 mg|Amlodipine 10 mg|Cilnidipine 10 mg|Metoprolol 25 mg|Metoprolol 50 mg|
Metoprolol XL 25 mg|Bisoprolol 5 mg|Atenolol 50 mg|Nebivolol 5 mg|Carvedilol 6.25 mg|Ramipril 5 mg|Enalapril 5 mg|Hydrochlorothiazide 12.5 mg|
Chlorthalidone 12.5 mg|Furosemide 40 mg|Torsemide 10 mg|Spironolactone 25 mg|Isosorbide Mononitrate 30 mg|Nitroglycerin 2.6 mg|Ranolazine 500 mg|
Ticagrelor 90 mg|Warfarin 5 mg|Apixaban 5 mg|Rivaroxaban 20 mg|Dabigatran 110 mg|Digoxin 0.25 mg|Amiodarone 200 mg|Ivabradine 5 mg|
Levothyroxine 25 mcg|Levothyroxine 50 mcg|Levothyroxine 75 mcg|Levothyroxine 100 mcg|Carbimazole 5 mg|Methimazole 10 mg|
Pantoprazole 40 mg|Rabeprazole 20 mg|Omeprazole 20 mg|Esomeprazole 40 mg|Famotidine 20 mg|Domperidone 10 mg|Ondansetron 4 mg|
Pantoprazole + Domperidone 40/30 mg|Rabeprazole + Domperidone 20/30 mg|Itopride 50 mg|Sucralfate 1 g|Lactulose syrup|Bisacodyl 5 mg|
Loperamide 2 mg|ORS sachet|Racecadotril 100 mg|Mebeverine 135 mg|Drotaverine 80 mg|Dicyclomine 10 mg|Ursodeoxycholic acid 300 mg|
Amoxicillin 500 mg|Amoxicillin + Clavulanate 625 mg|Azithromycin 500 mg|Azithromycin 250 mg|Cefixime 200 mg|Cefuroxime 500 mg|Cefpodoxime 200 mg|
Ciprofloxacin 500 mg|Levofloxacin 500 mg|Ofloxacin 200 mg|Doxycycline 100 mg|Metronidazole 400 mg|Nitrofurantoin 100 mg|Linezolid 600 mg|
Fluconazole 150 mg|Itraconazole 200 mg|Terbinafine 250 mg|Albendazole 400 mg|Ivermectin 12 mg|Acyclovir 400 mg|Valacyclovir 500 mg|
Hydroxychloroquine 200 mg|Cetirizine 10 mg|Levocetirizine 5 mg|Fexofenadine 120 mg|Fexofenadine 180 mg|Montelukast 10 mg|
Montelukast + Levocetirizine 10/5 mg|Bilastine 20 mg|Chlorpheniramine 4 mg|Salbutamol inhaler 100 mcg|Budesonide + Formoterol inhaler|
Fluticasone + Salmeterol inhaler|Tiotropium inhaler|Deriphyllin 150 mg|Ambroxol syrup|Dextromethorphan syrup|Guaifenesin syrup|
Prednisolone 5 mg|Prednisolone 10 mg|Methylprednisolone 4 mg|Deflazacort 6 mg|Dexamethasone 0.5 mg|
Vitamin D3 60000 IU|Vitamin D3 1000 IU|Calcium + Vitamin D3 500 mg|Vitamin B12 1500 mcg|Methylcobalamin 1500 mcg|Folic acid 5 mg|
Iron (ferrous ascorbate) 100 mg|Iron + Folic acid|Multivitamin|Zinc 50 mg|Vitamin C 500 mg|Omega-3 1000 mg|Magnesium 250 mg|
Alprazolam 0.25 mg|Clonazepam 0.5 mg|Escitalopram 10 mg|Sertraline 50 mg|Fluoxetine 20 mg|Paroxetine 12.5 mg|Amitriptyline 10 mg|
Duloxetine 30 mg|Mirtazapine 15 mg|Olanzapine 5 mg|Quetiapine 25 mg|Risperidone 2 mg|Zolpidem 10 mg|Melatonin 3 mg|
Gabapentin 300 mg|Pregabalin 75 mg|Pregabalin + Methylcobalamin 75/750 mcg|Levetiracetam 500 mg|Sodium Valproate 500 mg|Carbamazepine 200 mg|
Phenytoin 100 mg|Topiramate 25 mg|Donepezil 5 mg|Levodopa + Carbidopa 100/25 mg|Betahistine 16 mg|Cinnarizine 25 mg|Flunarizine 10 mg|
Tramadol 50 mg|Tapentadol 50 mg|Etoricoxib 90 mg|Thiocolchicoside 4 mg|Colchicine 0.5 mg|Febuxostat 40 mg|Allopurinol 100 mg|
Methotrexate 7.5 mg|Glucosamine 500 mg|Tamsulosin 0.4 mg|Silodosin 8 mg|Finasteride 5 mg|Dutasteride 0.5 mg|Sildenafil 50 mg|Tadalafil 5 mg|
Oral contraceptive (levonorgestrel + ethinylestradiol)|Progesterone 200 mg|Dydrogesterone 10 mg|Norethisterone 5 mg|Letrozole 2.5 mg|
Clomiphene 50 mg|Myo-inositol 2 g|Cabergoline 0.5 mg|Tranexamic acid 500 mg|Mefenamic acid 500 mg|Alendronate 70 mg|
Sodium bicarbonate 500 mg|Calcium acetate 667 mg|Sevelamer 800 mg|Potassium chloride syrup|Erythropoietin injection|
Timolol eye drops 0.5%|Latanoprost eye drops|Moxifloxacin eye drops|Carboxymethylcellulose eye drops|Mupirocin ointment|Clotrimazole cream|
Betamethasone cream|Hydrocortisone cream|Calamine lotion|Povidone-iodine solution|Silver sulfadiazine cream"""
NAMES = [x.strip() for x in COMMON.replace("\n", "").split("|") if x.strip()]
