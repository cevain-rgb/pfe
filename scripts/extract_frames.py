import cv2
import os
import argparse

def extract_frames(video_path, output_dir, interval_sec=1.0, max_frames=None):
    """
    Extrait des frames d'une vidéo à intervalles réguliers.
    
    Args:
        video_path (str): Chemin vers le fichier vidéo.
        output_dir (str): Dossier de sortie pour les images.
        interval_sec (float): Intervalle en secondes entre deux frames extraites.
        max_frames (int, optional): Nombre max de frames à extraire.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Erreur : impossible d'ouvrir la vidéo {video_path}")
        return
    
    fps = cap.get(cv2.CAP_PROP_FPS)          # images par seconde
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    
    print(f"Vidéo : {video_path}")
    print(f"FPS : {fps:.2f} | Frames totales : {total_frames} | Durée : {duration:.2f}s")
    print(f"Extraction toutes les {interval_sec}s -> {fps * interval_sec:.1f} frames")
    
    frame_interval = int(fps * interval_sec)  # nombre de frames entre deux extractions
    if frame_interval < 1:
        frame_interval = 1
    
    count = 0
    saved = 0
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if count % frame_interval == 0:
            timestamp = count / fps
            filename = f"{video_name}_frame{count:06d}s.jpg"
            filepath = os.path.join(output_dir, filename)
            cv2.imwrite(filepath, frame)
            saved += 1
            print(f"[{saved}] {filename} time:{timestamp:.2f}")
            
            if max_frames and saved >= max_frames:
                break
        
        count += 1
    
    cap.release()
    print(f"\nTerminé. {saved} images extraites dans '{output_dir}'.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extraire des frames d'une vidéo pour annotation")
    parser.add_argument("video", help="Chemin du fichier vidéo")
    parser.add_argument("-o", "--output", default="./extracted_frames", help="Dossier de sortie")
    parser.add_argument("-i", "--interval", type=float, default=1.0, 
                        help="Intervalle en secondes entre frames (défaut: 1.0)")
    parser.add_argument("-n", "--max-frames", type=int, default=None,
                        help="Nombre maximal de frames à extraire")
    args = parser.parse_args()
    
    extract_frames(args.video, args.output, args.interval, args.max_frames)
