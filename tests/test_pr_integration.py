"""Regression checks for CLI compatibility and DEB/RPM packaging changes."""

import io
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from cli import create_parser, merge_config
from core.appimage import AppImageInfo
from local_deb.deb_builder import DebBuilder
from local_rpm.rpm_builder import RpmBuilder


def make_builder(builder_type):
    info = AppImageInfo()
    info.name = 'demo'
    info.version = '1.2.3-rc1'
    with patch.object(builder_type, '_check_dependencies'):
        return builder_type(info, '')


class ConfigurationTests(unittest.TestCase):
    def merge(self, config, *options):
        args = create_parser().parse_args(['demo.AppImage', '--config', 'example.json', *options])
        with patch('cli.load_config_file', return_value=config):
            return merge_config(args)

    def test_legacy_flags_override_nested_configuration(self):
        config = self.merge({
            'deb': {'section': 'utils', 'priority': 'extra', 'depends': ['old-deb']},
            'rpm': {'section': 'Applications/System', 'requires': ['old-rpm']},
        }, '--section', 'graphics', '--priority', 'optional', '--depends', 'shared-lib')
        deb = make_builder(DebBuilder)
        rpm = make_builder(RpmBuilder)
        deb.set_package_config(config)
        rpm.set_package_config(config)
        self.assertEqual(deb._get_section('deb'), 'graphics')
        self.assertEqual(deb._get_priority('deb'), 'optional')
        self.assertEqual(deb._get_dependencies('deb'), ['shared-lib'])
        self.assertEqual(rpm._get_requires('rpm'), ['shared-lib'])
        self.assertEqual(rpm._get_section('rpm'), 'Applications/System')

    def test_missing_flags_preserve_independent_configuration(self):
        original = {
            'deb': {'section': 'graphics', 'priority': 'extra', 'depends': ['libc6']},
            'rpm': {'section': 'Applications/Graphics', 'requires': ['glibc']},
        }
        self.assertEqual(self.merge(original.copy()), original)

    def test_flat_configuration_remains_supported(self):
        config = self.merge({'section': 'utils', 'priority': 'optional',
                             'depends': ['libc6'], 'requires': ['glibc']})
        for builder_type, package_type in [(DebBuilder, 'deb'), (RpmBuilder, 'rpm')]:
            builder = make_builder(builder_type)
            builder.set_package_config(config)
            self.assertEqual(builder._get_section(package_type), 'utils')
            self.assertEqual(builder._get_dependencies(package_type), ['libc6'])
            self.assertEqual(builder._get_requires(package_type), ['glibc'])

    def test_explicit_architecture_is_converted_for_rpm(self):
        builder = make_builder(RpmBuilder)
        for deb_arch, rpm_arch in [('amd64', 'x86_64'), ('arm64', 'aarch64'),
                                  ('armhf', 'armv7hl'), ('i386', 'i686')]:
            with self.subTest(architecture=deb_arch):
                builder.set_package_config({'architecture': deb_arch})
                self.assertEqual(builder.get_architecture('deb'), deb_arch)
                self.assertEqual(builder.get_architecture('rpm'), rpm_arch)

    def test_rpm_spec_uses_its_own_dependencies_and_valid_version(self):
        builder = make_builder(RpmBuilder)
        builder.set_package_config({
            'architecture': 'arm64',
            'deb': {'depends': ['libc6']},
            'rpm': {'requires': ['glibc'], 'section': 'Applications/Graphics'},
        })
        with tempfile.TemporaryDirectory() as directory:
            builder.build_dir = directory
            builder.rpm_build_dir = str(Path(directory) / 'BUILD')
            builder.spec_file = str(Path(directory) / 'demo.spec')
            builder.create_package_structure()
            builder.generate_metadata_files()
            spec = Path(builder.spec_file).read_text()
            self.assertIn('Version:        1.2.3~rc1', spec)
            self.assertIn('Requires:       glibc', spec)
            self.assertIn('BuildArch:      aarch64', spec)
            self.assertIn('Group:          Applications/Graphics', spec)
            self.assertNotIn('URL:', spec)
            self.assertNotIn('Requires:       libc6', spec)


@unittest.skipUnless(shutil.which('ar'), 'manual DEB packaging requires ar')
class ManualDebTests(unittest.TestCase):
    def test_real_archive_contains_root_control_and_preserves_payload(self):
        builder = make_builder(DebBuilder)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build = root / 'build'
            control_dir = build / 'DEBIAN'
            control_dir.mkdir(parents=True)
            builder.build_dir = str(build)
            builder.debian_dir = str(control_dir)
            builder.set_package_config({'architecture': 'amd64'})
            builder.generate_metadata_files()
            payload = build / 'usr/bin/demo'
            payload.parent.mkdir(parents=True)
            payload.write_text('#!/bin/sh\necho demo\n')
            payload.chmod(0o755)
            link = payload.with_name('demo-link')
            link.symlink_to('demo')
            long_file = build / 'usr/share' / ('x' * 120)
            long_file.parent.mkdir(parents=True)
            long_file.write_text('long path payload')
            output = root / 'output/demo.deb'
            output.parent.mkdir()
            output.write_bytes(b'old output must be replaced')

            with redirect_stdout(io.StringIO()):
                builder._build_deb_manually(str(output))
            members = subprocess.check_output(['ar', 't', str(output)], text=True).splitlines()
            self.assertEqual(members, ['debian-binary', 'control.tar.gz', 'data.tar.gz'])
            self.assertEqual(subprocess.check_output(['ar', 'p', str(output), 'debian-binary']), b'2.0\n')

            for name in ['control.tar.gz', 'data.tar.gz']:
                content = subprocess.check_output(['ar', 'p', str(output), name])
                with tarfile.open(fileobj=io.BytesIO(content), mode='r:gz') as archive:
                    for member in archive.getmembers():
                        self.assertEqual((member.uid, member.gid), (0, 0))
                        self.assertEqual((member.uname, member.gname), ('root', 'root'))
                    if name == 'control.tar.gz':
                        self.assertIn('./control', archive.getnames())
                        self.assertNotIn('DEBIAN/control', archive.getnames())
                        self.assertEqual(archive.getmember('./postinst').mode & 0o111, 0o111)
                    else:
                        self.assertFalse(any(n.startswith('DEBIAN') for n in archive.getnames()))
                        self.assertEqual(archive.extractfile('usr/bin/demo').read(), payload.read_bytes())
                        self.assertEqual(archive.getmember('usr/bin/demo').mode, 0o755)
                        self.assertEqual(archive.getmember('usr/bin/demo-link').linkname, 'demo')
                        self.assertEqual(archive.extractfile('usr/share/' + 'x' * 120).read(), b'long path payload')

            if shutil.which('dpkg-deb'):
                package = subprocess.check_output(['dpkg-deb', '--field', str(output), 'Package'], text=True)
                self.assertEqual(package.strip(), 'demo')
                subprocess.run(['dpkg-deb', '--contents', str(output)], check=True, capture_output=True)


if __name__ == '__main__':
    unittest.main()
