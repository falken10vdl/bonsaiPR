import os

class Settings:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.scripts_dir = os.path.join(self.base_dir, 'scripts')
        self.logs_dir = os.path.join(self.base_dir, 'logs')
        self.env_file = os.path.join(self.base_dir, '.env')
        self.requirements_file = os.path.join(self.base_dir, 'requirements.txt')

    def get_scripts(self):
        return [
            os.path.join(self.scripts_dir, '00_clone_merge_and_replace.py'),
            os.path.join(self.scripts_dir, '01_build_bonsaiPR_addons.py'),
            os.path.join(self.scripts_dir, '02_upload_to_falken10vdl.py'),
            os.path.join(self.scripts_dir, '03_upload_mergedPR.py')
        ]

    def get_log_file(self):
        return os.path.join(self.logs_dir, 'automation.log')

    def get_env_file(self):
        return self.env_file

    def get_requirements_file(self):
        return self.requirements_file