import os
import os.path
import shutil
import subprocess
import tempfile
import win32file

from nose.tools import assert_raises, eq_

import dbdb
import dbdb.tool

class TestDatabase(object):
    def setup(self):
        self.temp_dir = os.path.join(os.getcwd(), "temp1")
        if not os.path.exists(self.temp_dir):
            os.mkdir(self.temp_dir)
        self.new_tempfile_name = os.path.join(self.temp_dir, "new.db")
        self.tempfile_name = os.path.join(self.temp_dir, 'existing.db')
        open(self.tempfile_name, 'w').close()

    def teardown(self):
        shutil.rmtree(self.temp_dir)

    def test_new_database_file(self):
        db = dbdb.connect(self.new_tempfile_name)
        db['a'] = 'aye'
        db.commit()
        db.close()

    def test_persistence(self):
        db = dbdb.connect(self.tempfile_name)
        db['b'] = 'bee'
        db['a'] = 'aye'
        db['c'] = 'see'
        db.commit()
        db['d'] = 'dee'
        eq_(len(db), 4)
        db['f'] = 'fff'
        db.close()
        db = dbdb.connect(self.tempfile_name)
        eq_(db['a'], 'aye')
        eq_(db['b'], 'bee')
        eq_(db['c'], 'see')
        with assert_raises(KeyError):
            db['d']
        eq_(len(db), 3)
        db.close()

class TestTool(object):
    def setup(self):
        self.tempfile_name = os.path.join(os.getcwd(), "temp2.db")
        open(self.tempfile_name, 'w').close()
        
    def teardown(self):
        os.remove(self.tempfile_name)

    def _tool(self, *args):
        return subprocess.check_output(
            ['python', '-m', 'dbdb.tool', self.tempfile_name] + list(args),
            stderr=subprocess.STDOUT,
        )

    def test_get_non_existent(self):
        self._tool('set', 'a', b'b')
        self._tool('delete', 'a')
        with assert_raises(subprocess.CalledProcessError) as raised:
            self._tool('get', 'a')
        eq_(raised.exception.returncode, dbdb.tool.BAD_KEY)
    
    def test_tool(self):
        expected = b'b'
        self._tool('set', 'a', expected)
        actual = self._tool('get', 'a')
        eq_(actual, expected)

    