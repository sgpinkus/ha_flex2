"""Config flow for flex2."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DOMAIN, CONF_P_L, CONF_P_H, CONF_PRICE_ENTITY, DEFAULT_P_L, DEFAULT_P_H


class Flex2ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            p_l = user_input[CONF_P_L]
            p_h = user_input[CONF_P_H]
            if p_h <= p_l:
                errors["base"] = "p_h_must_exceed_p_l"
            elif p_h >= 0 or p_l >= 0:
                errors["base"] = "load_device_requires_negative_params"
            else:
                return self.async_create_entry(title="HA Flex", data=user_input)

        schema = vol.Schema({
            vol.Required(CONF_PRICE_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["input_number", "sensor"])
            ),
            vol.Required(CONF_P_L, default=DEFAULT_P_L): selector.NumberSelector(
                selector.NumberSelectorConfig(min=-1e6, max=0, step=0.01, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(CONF_P_H, default=DEFAULT_P_H): selector.NumberSelector(
                selector.NumberSelectorConfig(min=-1e6, max=0, step=0.01, mode=selector.NumberSelectorMode.BOX)
            ),
        })

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return HaFlexOptionsFlow(config_entry)


class HaFlexOptionsFlow(config_entries.OptionsFlow):

    def __init__(self, config_entry):
        self._entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}
        current = self._entry.options or self._entry.data

        if user_input is not None:
            if user_input[CONF_P_H] <= user_input[CONF_P_L]:
                errors["base"] = "p_h_must_exceed_p_l"
            else:
                return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema({
            vol.Required(CONF_P_L, default=current.get(CONF_P_L, DEFAULT_P_L)):
                selector.NumberSelector(
                    selector.NumberSelectorConfig(min=-10, max=-0.01, step=0.01, mode=selector.NumberSelectorMode.BOX)
                ),
            vol.Required(CONF_P_H, default=current.get(CONF_P_H, DEFAULT_P_H)):
                selector.NumberSelector(
                    selector.NumberSelectorConfig(min=-9.99, max=-0.001, step=0.01, mode=selector.NumberSelectorMode.BOX)
                ),
        })

        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)