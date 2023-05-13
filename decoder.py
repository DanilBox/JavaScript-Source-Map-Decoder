import argparse
import json
import sys
from pathlib import Path
from typing import Any, TypedDict

from common import source_maps
from common.error import Error
from common.safe_path import safe_path_join

FORBIDDEN_SYMBOL_LIST = ["|", "{", "}", "$", "^"]
RENAMED_SYMBOL_LIST = [" "]


class DecoderStatistic(TypedDict):
    forbiddenPaths: list[str]
    renamedPaths: dict[str, str]
    deduplicated: dict[str, str]


def check_in_forbidden_symbols(file_path: str) -> bool:
    for forbidden_symbol in FORBIDDEN_SYMBOL_LIST:
        if forbidden_symbol in file_path:
            return True

    return False


def remove_renamed_symbols(file_path: str) -> str:
    for symbol in RENAMED_SYMBOL_LIST:
        file_path = file_path.replace(symbol, "_")

    return file_path


def get_saved_folder(map_file: Path) -> str:
    suffixes = [".map", ".js"]

    file_name = map_file.name
    for suffix in suffixes:
        file_name = file_name.removesuffix(suffix)

    assert not file_name.endswith(".js") and not file_name.endswith(".map"), "Не правильно удалились расширения"
    return file_name


def save_statistic_file(output_file_folder: Path, statistic: Any) -> None:
    output_file_folder.write_text(json.dumps(statistic, indent=2))


def remove_first_slash(file_path: str) -> str:
    while file_path.startswith("/"):
        file_path = file_path.removeprefix("/")

    return file_path


def save_decode_result(output_folder: Path, bundle_name: str, decode_result: source_maps.DecodeResult) -> None:
    folder_path = output_folder / bundle_name
    if not folder_path.exists():
        folder_path.mkdir()

    files_folder_path = folder_path / "files"
    if not files_folder_path.exists():
        files_folder_path.mkdir()

    forbidden_paths: list[str] = []
    renamed_paths: dict[str, str] = {}
    deduplicated: dict[str, str] = {}

    # Папка в который лежит бандл, относительной данной папки, мы и будет сохранять файлы
    relative_folder_in_sm = Path(decode_result.sourceMapStatistic["sourceMapPath"]).parent
    for file_path, file_content in decode_result.files.items():
        if check_in_forbidden_symbols(file_path):
            forbidden_paths.append(file_path)
            print("[INFO]", f"Файл '{file_path}' был убран для сохранения")
            continue

        if (new_value := remove_renamed_symbols(file_path)) != file_path:
            renamed_paths[file_path] = new_value
            print("[INFO]", f"Файл '{file_path}' был переименован")
            file_path = new_value

        # Убираем первый '/', что-бы не попасть в корень диска
        file_path = remove_first_slash(file_path)

        # Путь восстанавливаемого файла в Sources Map
        file_path_in_sm = relative_folder_in_sm / file_path

        saved_file_path = safe_path_join(files_folder_path, file_path_in_sm)
        if not saved_file_path.parent.exists():
            saved_file_path.parent.mkdir(parents=True)

        if saved_file_path.exists():
            old_file_path = str(saved_file_path)
            print("[INFO]", f"Задублирование файла '{saved_file_path}'")

            saved_file_path = Path(f"{saved_file_path}?dep2")
            deduplicated[old_file_path] = str(saved_file_path)

        saved_file_path.write_text(file_content)

    decoder_statistic = DecoderStatistic(
        forbiddenPaths=forbidden_paths,
        renamedPaths=renamed_paths,
        deduplicated=deduplicated,
    )

    save_statistic_file(folder_path / "statistic.json", decode_result.sourceMapStatistic)
    save_statistic_file(folder_path / "decoder.json", decoder_statistic)


def get_sources_maps_files(input_path: Path) -> list[Path]:
    if not input_path.exists():
        exit(f"Файл или папки '{input_path}' не существует")

    if input_path.is_dir():
        return [file for file in input_path.glob("*.map") if file.is_file()]

    if input_path.is_file():
        return [input_path]

    exit(f"Невозможно определить тип пути: {input_path}")


def decoder(input_path: str, output_folder: str) -> None:
    output_path = Path(output_folder)
    if output_path.exists():
        print("[WARNING]", f"Папка '{output_folder}', уже существует, возможны ошибки при работе программы")
    else:
        output_path.mkdir(parents=True)

    sm_files = get_sources_maps_files(Path(input_path))
    for sm_file in sm_files:
        result = source_maps.decode(sm_file.read_text(encoding="utf-8"))
        if isinstance(result, Error):
            print("[ERROR]", f"Произошла ошибка при декодировании файла '{sm_file}': {result.message}")
            continue

        bundle_name = get_saved_folder(sm_file)
        save_decode_result(output_path, bundle_name, result)


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="JavaScript Source Maps Decoder")
    parser.add_argument(
        "-I",
        "--input",
        dest="input_path",
        type=str,
        required=True,
        help="Путь до файла или директории c Source Map",
    )
    parser.add_argument(
        "-O",
        "--output",
        dest="output_folder",
        type=str,
        default="output",
        help="Путь до папки для вывода",
    )

    args = parser.parse_args(argv)
    decoder(**vars(args))


if __name__ == "__main__":
    main(sys.argv[1::])
