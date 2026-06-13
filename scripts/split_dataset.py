import os
import random
import shutil

# ===== PARAMÈTRES =====
images_dir = "./dataset_non_split/images"      # dossier contenant les images originales
labels_dir = "./dataset_non_split/labels"      # dossier contenant les annotations .txt
output_dir = "./dataset"       # dossier de sortie
train_ratio = 0.7
val_ratio   = 0.2
test_ratio  = 0.1
seed = 42
# =======================

random.seed(seed)

# 1. Récupérer toutes les images (sans extension)
image_files = [f for f in os.listdir(images_dir) if f.endswith(('.jpg','.jpeg','.png'))]
base_names = [os.path.splitext(f)[0] for f in image_files]

# 2. Garder seulement celles qui ont un fichier .txt correspondant
valid_names = [name for name in base_names if os.path.exists(os.path.join(labels_dir, name+'.txt'))]
print(f"Paires image+label trouvées : {len(valid_names)}")

# 3. Mélanger et répartir
random.shuffle(valid_names)
total = len(valid_names)
train_end = int(train_ratio * total)
val_end = train_end + int(val_ratio * total)

train_names = valid_names[:train_end]
val_names   = valid_names[train_end:val_end]
test_names  = valid_names[val_end:]

# 4. Créer les dossiers de sortie
splits = {'train': train_names, 'val': val_names, 'test': test_names}
for split in splits:
    os.makedirs(os.path.join(output_dir, 'images', split), exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'labels', split), exist_ok=True)

# 5. Copier les fichiers
for split, names in splits.items():
    print(f"{split}: {len(names)} images")
    for name in names:
        # trouver l'extension réelle de l'image
        img_ext = None
        for ext in ('.jpg','.jpeg','.png'):
            if os.path.exists(os.path.join(images_dir, name+ext)):
                img_ext = ext
                break
        if img_ext is None:
            continue
        shutil.copy(os.path.join(images_dir, name+img_ext),
                    os.path.join(output_dir, 'images', split, name+img_ext))
        shutil.copy(os.path.join(labels_dir, name+'.txt'),
                    os.path.join(output_dir, 'labels', split, name+'.txt'))

print("Terminé !")
