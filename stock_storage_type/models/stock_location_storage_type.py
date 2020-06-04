# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.base_m2m_custom_field.fields import Many2manyCustom

_logger = logging.getLogger(__name__)


class StockLocationStorageType(models.Model):

    _name = "stock.location.storage.type"
    _description = "Location storage type"

    name = fields.Char(required=True)
    location_ids = fields.Many2many(
        "stock.location",
        "stock_location_stock_location_storage_type_rel",
        "stock_location_storage_type_id",
        "stock_location_id",
    )

    package_storage_type_ids = Many2manyCustom(
        "stock.package.storage.type",
        "stock_location_package_storage_type_rel",
        "location_storage_type_id",
        "package_storage_type_id",
        create_table=False,
        string="Allowed packages storage types",
        help="Package storage types that are allowed on locations "
        "where this location storage type is defined.",
    )

    only_empty = fields.Boolean(
        help="If checked, moves to the destination location will only be "
        "allowed if there are not any existing quant nor planned move on "
        "this location"
    )
    do_not_mix_lots = fields.Boolean(
        help="If checked, moves to the destination location will only be "
        "allowed if the location contains product of the same "
        "lot."
    )
    do_not_mix_products = fields.Boolean(
        help="If checked, moves to the destination location will only be "
        "allowed if the location contains the same product."
    )
    max_height = fields.Float(
        string="Max height (mm)",
        help="If defined, moves to the destination location will only be "
        "allowed if the packaging height is lower than this maximum.",
    )
    max_weight = fields.Float(
        string="Max weight (kg)",
        help="If defined, moves to the destination location will only be "
        "allowed if the packaging wight is lower than this maximum.",
    )
    has_restrictions = fields.Boolean(compute="_compute_has_restrictions")

    @api.constrains("only_empty", "do_not_mix_lots", "do_not_mix_products")
    def _check_empty_mix(self):
        for location_storage_type in self:
            if location_storage_type.only_empty and (
                location_storage_type.do_not_mix_lots
                or location_storage_type.do_not_mix_products
            ):
                raise ValidationError(
                    _(
                        "You cannot set 'Do not mix lots' or 'Do not mix products'"
                        " with 'Only empty' constraint."
                    )
                )

    @api.constrains("do_not_mix_lots", "do_not_mix_products")
    def _check_do_not_mix(self):
        for location_storage_type in self:
            if (
                location_storage_type.do_not_mix_lots
                and not location_storage_type.do_not_mix_products
            ):
                raise ValidationError(
                    _(
                        "You cannot set 'Do not mix lots' without setting 'Do not"
                        " mix products' constraint."
                    )
                )

    @api.onchange("do_not_mix_products")
    def _onchange_do_not_mix_products(self):
        if not self.do_not_mix_products:
            self.do_not_mix_lots = False

    @api.depends(
        "only_empty",
        "do_not_mix_lots",
        "do_not_mix_products",
        "max_height",
        "max_weight",
    )
    def _compute_has_restrictions(self):
        for slst in self:
            slst.has_restrictions = any(
                [
                    slst.only_empty,
                    slst.do_not_mix_lots,
                    slst.do_not_mix_products,
                    slst.max_height,
                    slst.max_weight,
                ]
            )

    def _domain_location_storage_type(self, candidate_locations, quants, products):
        """compute a domain which applies the constraint of the
        stock.location.storage.type to select locations among candidate
        locations.
        """
        self.ensure_one()
        location_domain = [
            ('id', 'in', candidate_locations.ids),
            ('allowed_location_storage_type_ids', '=', self.id),
        ]
        if self.only_empty:
            location_domain.append(
                ('location_is_empty', '=', True)
            )
        if self.do_not_mix_products:
            location_domain.append(
                ('location_will_contain_product_ids', 'not in', products.ids)
            )
            if self.do_not_mix_lots:
                lots = quants.mapped('lot_id')
                location_domain.append(
                    ('location_will_contain_lot_ids', 'not in', lots.ids),
                )
        return location_domain
