from lxml import etree

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase

from odoo.addons.project_matrix.models.project_project import MATRIX_BASE_URL_PARAM


class TestProjectMatrix(TransactionCase):

    def setUp(self):
        super().setUp()
        self.parameters = self.env['ir.config_parameter'].sudo()
        self.parameters.set_param(MATRIX_BASE_URL_PARAM, 'https://element.example.com')

    def test_url_is_normalized_to_room_id(self):
        project = self.env['project.project'].create({
            'name': 'Matrix project',
            'matrix_room_id': (
                'https://element.other.example/#/room/'
                '%21opaque-room%3Amatrix.example.com?via=matrix.example.com'
            ),
        })

        self.assertEqual(project.matrix_room_id, '!opaque-room:matrix.example.com')
        self.assertEqual(
            project.matrix_room_url,
            'https://element.example.com/#/room/'
            '!opaque-room:matrix.example.com',
        )

    def test_matrix_to_url_is_normalized(self):
        project = self.env['project.project'].create({
            'name': 'Matrix.to project',
            'matrix_room_id': (
                'https://matrix.to/#/!another-room:matrix.example.com'
                '?via=matrix.example.com'
            ),
        })

        self.assertEqual(project.matrix_room_id, '!another-room:matrix.example.com')

    def test_invalid_room_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.env['project.project'].create({
                'name': 'Invalid project',
                'matrix_room_id': 'https://element.example.com/#/room/no-room-id',
            })

    def test_existing_room_path_and_placeholder_are_supported(self):
        project_model = self.env['project.project']
        room_id = '!room:matrix.example.com'

        self.assertEqual(
            project_model._build_matrix_room_url(
                room_id, 'https://element.example.com/#/room/'
            ),
            'https://element.example.com/#/room/!room:matrix.example.com',
        )
        self.assertEqual(
            project_model._build_matrix_room_url(
                room_id, 'https://element.example.com/room/{room_id}'
            ),
            'https://element.example.com/room/!room:matrix.example.com',
        )

    def test_open_room_action(self):
        project = self.env['project.project'].create({
            'name': 'Matrix project',
            'matrix_room_id': '!room:matrix.example.com',
        })

        self.assertEqual(project.action_open_matrix_room(), {
            'type': 'ir.actions.act_url',
            'url': 'https://element.example.com/#/room/!room:matrix.example.com',
            'target': 'new',
        })

    def test_open_room_requires_base_url(self):
        project = self.env['project.project'].create({
            'name': 'Matrix project',
            'matrix_room_id': '!room:matrix.example.com',
        })
        self.parameters.set_param(MATRIX_BASE_URL_PARAM, '')

        with self.assertRaises(UserError):
            project.action_open_matrix_room()

    def test_base_url_is_saved_as_system_parameter(self):
        settings = self.env['res.config.settings'].create({
            'matrix_base_url': 'https://chat.example.com',
        })

        settings.set_values()

        self.assertEqual(
            self.parameters.get_param(MATRIX_BASE_URL_PARAM),
            'https://chat.example.com',
        )

    def test_invalid_base_url_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.env['res.config.settings'].create({
                'matrix_base_url': 'not-an-http-url',
            })
        with self.assertRaises(ValidationError):
            self.env['res.config.settings'].create({
                'matrix_base_url': 'https://[invalid',
            })

    def test_matrix_room_is_in_project_header_details(self):
        view = self.env.ref('project.edit_project')
        arch = self.env['project.project'].get_view(view.id, 'form')['arch']
        document = etree.fromstring(arch)

        matrix_rows = document.xpath(
            "//div[@name='dates']/following-sibling::div[@name='matrix_room']"
        )
        self.assertEqual(len(matrix_rows), 1)
        self.assertTrue(matrix_rows[0].xpath(".//field[@name='matrix_room_id']"))
        self.assertTrue(matrix_rows[0].xpath(".//field[@name='matrix_room_url']"))
        allocated_hours = document.xpath(
            "//div[@name='dates']/following-sibling::field"
            "[@name='allocated_hours']"
        )
        if allocated_hours:
            detail_group_children = list(matrix_rows[0].getparent())
            self.assertLess(
                detail_group_children.index(allocated_hours[0]),
                detail_group_children.index(matrix_rows[0]),
            )
        self.assertFalse(
            document.xpath(
                "//page[@name='settings']//div[@name='matrix_room']"
            )
        )
