from urllib.parse import urlsplit

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .project_project import MATRIX_BASE_URL_PARAM


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    matrix_base_url = fields.Char(
        string='Element Base URL',
        config_parameter=MATRIX_BASE_URL_PARAM,
        help=(
            'Base URL of the Element installation, for example '
            'https://element.example.com.'
        ),
    )

    @api.constrains('matrix_base_url')
    def _check_matrix_base_url(self):
        for settings in self:
            if not settings.matrix_base_url:
                continue
            try:
                parsed_url = urlsplit(settings.matrix_base_url.strip())
            except ValueError:
                parsed_url = None
            if (
                not parsed_url
                or parsed_url.scheme not in ('http', 'https')
                or not parsed_url.netloc
            ):
                raise ValidationError(
                    _('The Element base URL must be a valid HTTP or HTTPS URL.')
                )
