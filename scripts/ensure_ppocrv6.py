from pathlib import Path
from huggingface_hub import snapshot_download
import hashlib, shutil

root=Path("/srv/hoopvision/models/cache/ppocrv6")
specs={
    "medium":{
        "repo":"PaddlePaddle/PP-OCRv6_medium_rec_safetensors",
        "revision":"024cad6a831de75c2c3c26e711ba8c4a82ccd24b",
        "hashes":{
            "model.safetensors":"5f43c16f2a684b1d2284662178bdb604febd3d6bfdb5ca73828d08d0f7c0c3e9",
            "config.json":"aa5f351b4a7df95cc4953f013d53a6d44205f1bb0aee0ec7eb243d1d8fae1c27",
            "preprocessor_config.json":"2b24fa36f548893f26a931cf44f1a1a6b2b14ed7e2f8f8e28e6848801a8278db",
        },
    },
    "small":{
        "repo":"PaddlePaddle/PP-OCRv6_small_rec_safetensors",
        "revision":"fe049fb103f57443fe8840c54ed06b702f3c1de5",
        "hashes":{
            "model.safetensors":"f65a332afe5aa663f0b9d5706f4ae8457b5b4058a842d5c1eb22df505c27d642",
            "config.json":"8693fd8485e8543e13d0f6dde3891a3f4af9a47fc4e3a391fbed71f8015c899e",
            "preprocessor_config.json":"2b24fa36f548893f26a931cf44f1a1a6b2b14ed7e2f8f8e28e6848801a8278db",
        },
    },
}
for name,spec in specs.items():
    dst=root/name
    dst.mkdir(parents=True,exist_ok=True)
    valid=all((dst/f).is_file() and hashlib.sha256((dst/f).read_bytes()).hexdigest()==h for f,h in spec["hashes"].items())
    if not valid:
        snap=Path(snapshot_download(repo_id=spec["repo"],revision=spec["revision"],allow_patterns=list(spec["hashes"])))
        for filename,expected in spec["hashes"].items():
            shutil.copyfile(snap/filename,dst/filename)
            got=hashlib.sha256((dst/filename).read_bytes()).hexdigest()
            if got!=expected:
                raise RuntimeError(f"{name} {filename} hash mismatch {got} != {expected}")
print("HOOPVISION_PPOCRV6_ASSETS_OK")
