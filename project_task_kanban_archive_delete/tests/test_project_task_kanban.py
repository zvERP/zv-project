from lxml import etree

from odoo.tests.common import TransactionCase


class TestProjectTaskKanban(TransactionCase):

    def _get_kanban_arch(self, view_xmlid):
        view = self.env.ref(view_xmlid)
        arch = self.env['project.task'].get_view(view.id, 'kanban')['arch']
        return etree.fromstring(arch)

    def test_my_tasks_kanban_has_archive_and_delete(self):
        arch = self._get_kanban_arch('project.view_task_kanban_inherit_my_task')
        menu = arch.xpath("//div[hasclass('o_dropdown_kanban')]")[0]
        self.assertTrue(menu.xpath(".//a[@type='object'][@name='action_archive']"))
        self.assertTrue(menu.xpath(".//a[@type='delete']"))

    def test_project_kanban_unchanged(self):
        arch = self._get_kanban_arch('project.view_task_kanban')
        self.assertFalse(arch.xpath("//a[@name='action_archive']"))
        self.assertFalse(arch.xpath("//a[@type='delete']"))

    def test_archive_task(self):
        project = self.env['project.project'].create({'name': 'Project'})
        task = self.env['project.task'].create({
            'name': 'Task',
            'project_id': project.id,
        })
        task.action_archive()
        self.assertFalse(task.active)
