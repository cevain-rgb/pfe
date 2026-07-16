"""
# Avec les classes explicites
python split_dataset.py \
  --images_dir ./mon_export/images \
  --labels_dir ./mon_export/labels \
  --output_dir ./dataset \
  --train_ratio 0.7 --val_ratio 0.2 --test_ratio 0.1 \
  --classes oeil_ouvert oeil_ferme baillement

# Avec les paramètres par défaut (ratios 70/20/10)
python split_dataset.py --images_dir ./images --labels_dir ./labels --classes oeil_ouvert oeil_ferme baillement
"""

import argparse
import os
import random
import shutil


#  CONFIGURATION 
def parse_args():
    parser = argparse.ArgumentParser(
        description="Répartit aléatoirement un dataset Label-Studio (images + labels YOLO) en train/val/test."
    )
    parser.add_argument("--images_dir", required=True,
                        help="Dossier contenant les images originales (.jpg, .jpeg, .png)")
    parser.add_argument("--labels_dir", required=True,
                        help="Dossier contenant les fichiers .txt au format YOLO")
    parser.add_argument("--output_dir", default="./dataset",
                        help="Dossier de sortie (défaut: ./dataset)")
    parser.add_argument("--train_ratio", type=float, default=0.7,
                        help="Proportion d'images pour l'entraînement (défaut: 0.7)")
    parser.add_argument("--val_ratio", type=float, default=0.2,
                        help="Proportion d'images pour la validation (défaut: 0.2)")
    parser.add_argument("--test_ratio", type=float, default=0.1,
                        help="Proportion d'images pour le test (défaut: 0.1)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Graine aléatoire pour reproductibilité")
    parser.add_argument("--classes", nargs='+', default=None,
                        help="Liste des noms de classes (ex: 'oeil_ouvert' 'oeil_ferme' 'baillement'). "
                             "Si non fourni, un squelette sera créé.")
    return parser.parse_args()


def main():
    args = parse_args()
    images_dir = args.images_dir
    labels_dir = args.labels_dir
    output_dir = args.output_dir
    seed = args.seed

    random.seed(seed)

    # Vérifier les dossiers d'entrée
    if not os.path.isdir(images_dir):
        raise FileNotFoundError(f"Dossier images introuvable : {images_dir}")
    if not os.path.isdir(labels_dir):
        raise FileNotFoundError(f"Dossier labels introuvable : {labels_dir}")

    # 1. Récupérer toutes les images
    image_files = [f for f in os.listdir(images_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    # Noms sans extension
    base_names = [os.path.splitext(f)[0] for f in image_files]

    # 2. Garder seulement les noms ayant un fichier .txt correspondant
    valid_names = []
    for name in base_names:
        if os.path.exists(os.path.join(labels_dir, name + '.txt')):
            valid_names.append(name)
        else:
            print(f"⚠️  Pas de label trouvé pour {name}, ignorée.")

    print(f"Paires image+label trouvées : {len(valid_names)}")
    if len(valid_names) == 0:
        print("Erreur : aucune paire valide. Vérifiez les dossiers et les extensions.")
        return

    # 3. Mélanger et découper
    random.shuffle(valid_names)
    total = len(valid_names)
    n_train = int(args.train_ratio * total)
    n_val = int(args.val_ratio * total)
    # Le reste va au test (pour éviter les arrondis et avoir exactement total)
    n_test = total - n_train - n_val

    train_names = valid_names[:n_train]
    val_names = valid_names[n_train:n_train + n_val]
    test_names = valid_names[n_train + n_val:]

    splits = {
        'train': train_names,
        'val': val_names,
        'test': test_names
    }

    # 4. Créer les dossiers de sortie
    for split in splits:
        os.makedirs(os.path.join(output_dir, 'images', split), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'labels', split), exist_ok=True)

    # 5. Copier les fichiers
    for split, names in splits.items():
        print(f"{split}: {len(names)} images")
        for name in names:
            # Trouver l'extension réelle de l'image
            img_ext = None
            for ext in ('.jpg', '.jpeg', '.png'):
                src_path = os.path.join(images_dir, name + ext)
                if os.path.exists(src_path):
                    img_ext = ext
                    break
            if img_ext is None:
                print(f"⚠️  Image introuvable pour {name}, ignorée.")
                continue

            # Copier image
            dst_img = os.path.join(output_dir, 'images', split, name + img_ext)
            shutil.copy2(os.path.join(images_dir, name + img_ext), dst_img)

            # Copier label
            src_label = os.path.join(labels_dir, name + '.txt')
            dst_label = os.path.join(output_dir, 'labels', split, name + '.txt')
            shutil.copy2(src_label, dst_label)

    # 6. Générer le fichier data.yaml
    classes = args.classes
    if classes is None:
        classes = []
        print("\nAucune classe fournie via --classes. Génération d'un squelette data.yaml avec une liste vide.")
    else:
        print(f"Classes : {classes}")

    yaml_path = os.path.join(output_dir, 'data.yaml')
    with open(yaml_path, 'w') as f:
        f.write(f"# Fichier généré automatiquement\n")
        f.write(f"path: {os.path.abspath(output_dir)}\n")
        f.write(f"train: images/train\n")
        f.write(f"val: images/val\n")
        f.write(f"test: images/test\n\n")
        f.write(f"nc: {len(classes)}\n")
        f.write(f"names: {classes}\n")

    print(f"\n✅ Dataset réparti avec succès dans '{output_dir}'")
    print(f"   Fichier data.yaml généré : {yaml_path}")
    print(f"   N'oubliez pas d'éditer data.yaml pour vérifier/saisir les noms de classes.")


if __name__ == "__main__":
    main()