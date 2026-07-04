import os
from pathlib import Path
import tempfile
import unittest

from SEILAPLAN.utils.path_handler import (
    calculate_path_candidates,
    get_absolute_path_from_relative,
    get_relative_path,
    is_remote_or_virtual,
)


class TestPathHandler(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def test_resolve_path_further_down(self):
        """
        /tmp/data/geodata.txt
        /tmp/seilaplan/project.json
        new:
        /tmp/user001/data/geodata.txt
        /tmp/user001/seilaplan/project.json

        1. find relative path to get from project to geodata
        ../data/geodata.txt

        2. Apply this relative path to new project path
        /tmp/user001/seilaplan/project.json -> /tmp/user001/data/geodata.txt
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)

            project_dir = base_dir / "seilaplan"
            project_dir.mkdir(parents=True)
            project_file = project_dir / "project.json"
            project_file.write_text("{}", encoding="utf-8")

            data_dir = base_dir / "data"
            data_dir.mkdir(parents=True)
            geodata_file = data_dir / "geodata.txt"
            geodata_file.write_text("content", encoding="utf-8")

            # Get relative path from project_file to geodata_file
            relative_path = get_relative_path(geodata_file, project_dir)
            self.assertEqual(relative_path, os.path.join("..", "data", "geodata.txt"))

            new_location = base_dir / "user001" / "seilaplan"
            new_location.mkdir(parents=True)

            new_geodata_path = get_absolute_path_from_relative(
                relative_path,
                new_location,
            )
            self.assertEqual(
                new_geodata_path,
                os.path.join(str(base_dir), "user001", "data", "geodata.txt"),
            )

    def test_resolve_path_further_up(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)

            project_dir = base_dir / "seilaplan"
            project_dir.mkdir(parents=True)
            project_file = project_dir / "project.json"
            project_file.write_text("{}", encoding="utf-8")

            data_dir = base_dir / "data"
            data_dir.mkdir(parents=True)
            geodata_file = data_dir / "geodata.txt"
            geodata_file.write_text("content", encoding="utf-8")

            # Get relative path from project_file to geodata_file
            relative_path = get_relative_path(geodata_file, project_dir)
            self.assertEqual(relative_path, os.path.join("..", "data", "geodata.txt"))

            new_location = base_dir / "down" / "seilaplan"
            new_location.mkdir(parents=True)

            new_geodata_path = get_absolute_path_from_relative(
                relative_path,
                new_location,
            )
            self.assertEqual(
                new_geodata_path,
                os.path.join(str(base_dir), "down", "data", "geodata.txt"),
            )

    def test_resolve_path_ignores_cloud_paths(self):
        project_path = r"/tmp/project/project.json"
        data_path = "s3://my-bucket/file.tif"
        relative_path = get_relative_path(data_path, project_path)

        self.assertEqual(relative_path, data_path)

        same_geodata_path = get_absolute_path_from_relative(relative_path, project_path)
        self.assertEqual(same_geodata_path, data_path)

    def test_resolve_path_handle_cloud_project_paths(self):
        project_path = r"s3://my-bucket/project.json"
        data_path = "/tmp/project/file.tif"
        relative_path = get_relative_path(data_path, project_path)

        self.assertEqual(relative_path, data_path)

        same_geodata_path = get_absolute_path_from_relative(relative_path, project_path)
        self.assertEqual(same_geodata_path, data_path)

    def test_calculate_path_candidate_with_local_paths_that_dont_exist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            first_path = base_dir / "first"
            first_path.mkdir(parents=True)
            second_path = base_dir / "second"
            second_path.mkdir(parents=True)

            # Relative path do not exist in any of the base path candidates
            path_candidates = calculate_path_candidates(
                "relative/file.txt", [str(first_path), str(second_path)]
            )
            self.assertEqual(
                path_candidates,
                [
                    str(first_path / "relative" / "file.txt"),
                    str(second_path / "relative" / "file.txt"),
                ],
            )

    def test_calculate_path_candidate_with_local_paths_that_partially_exist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            first_path = base_dir / "first"
            first_path.mkdir(parents=True)
            second_path = base_dir / "second"
            second_path.mkdir(parents=True)

            relative_path = first_path / "relative"
            relative_path.mkdir(parents=True)
            relative_file = relative_path / "file.txt"
            relative_file.write_text("content", encoding="utf-8")

            # Only one of these paths actually exists, but they should both be returned
            path_candidates = calculate_path_candidates(
                "relative/file.txt", [str(first_path), str(second_path)]
            )
            self.assertEqual(
                path_candidates,
                [str(relative_file), str(second_path / "relative" / "file.txt")],
            )

    def test_calculate_path_candidate_with_local_paths_that_do_exist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            first_path = base_dir / "first"
            first_path.mkdir(parents=True)
            second_path = base_dir / "second"
            second_path.mkdir(parents=True)

            relative_path1 = first_path / "relative"
            relative_path1.mkdir(parents=True)
            relative_file1 = relative_path1 / "file.txt"
            relative_file1.write_text("content", encoding="utf-8")

            relative_path2 = second_path / "relative"
            relative_path2.mkdir(parents=True)
            relative_file2 = relative_path2 / "file.txt"
            relative_file2.write_text("content", encoding="utf-8")

            path_candidates2 = calculate_path_candidates(
                "relative/file.txt", [str(first_path), str(second_path)]
            )
            self.assertEqual(
                path_candidates2, [str(relative_file1), str(relative_file2)]
            )

    def test_calculate_path_candidate_with_streamed_geotiff(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            first_path = base_dir / "first"
            first_path.mkdir(parents=True)
            second_path = base_dir / "second"
            second_path.mkdir(parents=True)

            cog_path = "/vsicurl/https://data.geo.admin.ch/ch.swisstopo.swissalti3d/swissalti3d_2025_2630-1201/swissalti3d_2025_2630-1201_2_2056_5728.tif"

            path_candidates = calculate_path_candidates(
                cog_path, [str(first_path), str(second_path)]
            )
            self.assertEqual(path_candidates[0], cog_path)

    def test_is_remote_or_virtual_detects_gdal_virtual_paths(self):
        self.assertTrue(is_remote_or_virtual("/vsicurl/https://example.com/file.tif"))
        self.assertTrue(is_remote_or_virtual("/vsizip//tmp/archive.zip/file.tif"))
        self.assertTrue(is_remote_or_virtual("/vsis3/my-bucket/file.tif"))

    def test_is_remote_or_virtual_detects_cloud_schemes(self):
        self.assertTrue(is_remote_or_virtual("s3://my-bucket/file.tif"))
        self.assertTrue(is_remote_or_virtual("gs://my-bucket/file.tif"))
        self.assertTrue(is_remote_or_virtual("https://example.com/file.tif"))
        self.assertTrue(is_remote_or_virtual("ftp://example.com/file.tif"))

    def test_is_remote_or_virtual_returns_false_for_local_paths(self):
        self.assertFalse(is_remote_or_virtual("/tmp/file.tif"))
        self.assertFalse(is_remote_or_virtual("relative/file.tif"))
        self.assertFalse(is_remote_or_virtual(Path("/tmp/file.tif")))


if __name__ == "__main__":
    unittest.main()
