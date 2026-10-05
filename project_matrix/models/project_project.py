import re
from urllib.parse import quote, unquote, urlsplit

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


MATRIX_BASE_URL_PARAM = 'project_matrix.base_url'

# Room IDs are opaque.  Rooms up to version 11 include a server name, while
# version 12 IDs are URL-safe hashes without one.  Accept both formats so URLs
# copied from recent Element/Synapse installations can also be stored.
MATRIX_ROOM_ID_RE = re.compile(
    r'![A-Za-z0-9._~+/=-]+'
    r'(?::(?:\[[0-9A-Fa-f:.]+\]|[A-Za-z0-9.-]+)(?::[0-9]+)?)?'
)


class ProjectProject(models.Model):
    _inherit = 'project.project'

    matrix_room_id = fields.Char(
        string='Matrix Room ID',
        copy=False,
        help=(
            'Internal Matrix room ID. You may paste an Element or matrix.to '
            'room URL; only its ID (for example !room:example.com) is stored.'
        ),
    )
    matrix_room_url = fields.Char(
        string='Matrix Room URL',
        compute='_compute_matrix_room_url',
    )

    @api.model
    def _extract_matrix_room_id(self, value):
        if not value:
            return False
        decoded_value = unquote(value.strip())
        match = MATRIX_ROOM_ID_RE.search(decoded_value)
        if not match:
            raise ValidationError(
                _(
                    'The Matrix room must be an internal room ID beginning '
                    'with "!" or a URL containing one.'
                )
            )
        return match.group(0)

    @api.model
    def _get_matrix_base_url(self):
        return (
            self.env['ir.config_parameter']
            .sudo()
            .get_param(MATRIX_BASE_URL_PARAM, '')
            .strip()
        )

    @api.model
    def _build_matrix_room_url(self, room_id, base_url=None):
        if not room_id:
            return False
        base_url = (base_url or self._get_matrix_base_url()).strip().rstrip('/')
        try:
            parsed_url = urlsplit(base_url)
        except ValueError:
            return False
        if parsed_url.scheme not in ('http', 'https') or not parsed_url.netloc:
            return False

        encoded_room_id = quote(room_id, safe='!:[]')
        if '{room_id}' in base_url:
            return base_url.replace('{room_id}', encoded_room_id)
        if base_url.endswith('#/room'):
            return '%s/%s' % (base_url, encoded_room_id)
        return '%s/#/room/%s' % (base_url, encoded_room_id)

    @api.depends('matrix_room_id')
    def _compute_matrix_room_url(self):
        base_url = self._get_matrix_base_url()
        for project in self:
            project.matrix_room_url = project._build_matrix_room_url(
                project.matrix_room_id, base_url=base_url
            )

    @api.model_create_multi
    def create(self, vals_list):
        normalized_vals_list = []
        for vals in vals_list:
            vals = dict(vals)
            if 'matrix_room_id' in vals:
                vals['matrix_room_id'] = self._extract_matrix_room_id(
                    vals['matrix_room_id']
                )
            normalized_vals_list.append(vals)
        return super().create(normalized_vals_list)

    def write(self, vals):
        vals = dict(vals)
        if 'matrix_room_id' in vals:
            vals['matrix_room_id'] = self._extract_matrix_room_id(
                vals['matrix_room_id']
            )
        return super().write(vals)

    def action_open_matrix_room(self):
        self.ensure_one()
        if not self.matrix_room_id:
            raise UserError(_('This project does not have a Matrix room.'))
        room_url = self._build_matrix_room_url(self.matrix_room_id)
        if not room_url:
            raise UserError(
                _(
                    'Configure a valid Matrix base URL in the Project '
                    'settings before opening the room.'
                )
            )
        return {
            'type': 'ir.actions.act_url',
            'url': room_url,
            'target': 'new',
        }
