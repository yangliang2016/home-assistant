"""
Provide pre-made queries on top of the recorder component.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/history/
"""
import logging
from collections import defaultdict
from datetime import timedelta
from itertools import groupby

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util
from homeassistant.components import recorder, script
from homeassistant.components.frontend import register_built_in_panel
from homeassistant.components.http import HomeAssistantView

DOMAIN = 'history'
DEPENDENCIES = ['recorder', 'http']

_LOGGER = logging.getLogger(__name__)

SIGNIFICANT_DOMAINS = ('thermostat',)
IGNORE_DOMAINS = ('zone', 'scene',)

CONF_WHITELIST = 'whitelist'
CONF_WHITELIST_ENTITIES = 'whitelist_entities'
CONF_WHITELIST_DOMAINS = 'whitelist_domains'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        CONF_WHITELIST: vol.Schema({
            vol.Optional(CONF_WHITELIST_ENTITIES, default=[]): cv.ensure_list,
            vol.Optional(CONF_WHITELIST_DOMAINS, default=[]): cv.ensure_list
        }),
    }),
}, extra=vol.ALLOW_EXTRA)


def last_5_states(entity_id):
    """Return the last 5 states for entity_id."""
    entity_id = entity_id.lower()

    states = recorder.get_model('States')
    return recorder.execute(
        recorder.query('States').filter(
            (states.entity_id == entity_id) &
            (states.last_changed == states.last_updated)
        ).order_by(states.state_id.desc()).limit(5))


def get_significant_states(start_time, end_time=None, entity_id=None, config=None):
    """
    Return states changes during UTC period start_time - end_time.

    Significant states are all states where there is a state change,
    as well as all states from certain domains (for instance
    thermostat so that we get current temperature in our graphs).

    If whitelist was specified, select only domains or entities specified.
    """
    states = recorder.get_model('States')

    whitelist = config[DOMAIN].get(CONF_WHITELIST, None)
    if whitelist:
        whitelist_entities = whitelist[CONF_WHITELIST_ENTITIES]
        whitelist_domains = whitelist[CONF_WHITELIST_DOMAINS]
        _LOGGER.debug("DEBUGG entities %s", whitelist_entities)
        _LOGGER.debug("DEBUGG domains %s", whitelist_domains)
        if (whitelist_entities and whitelist_domains):
            _LOGGER.debug("DEBUGG process 2 %s", states)
            query = recorder.query('States').filter(
                (states.domain.in_(whitelist_domains) |
                (states.entity_id.in_(whitelist_entities))))

        elif whitelist_entities and not whitelist_domains:
            _LOGGER.debug("DEBUGG process entities %s", states)
            query = recorder.query('States').filter(
                (states.entity_id.in_(whitelist_entities)))

        else:
            _LOGGER.debug("DEBUGG process domains %s", states)
            query = recorder.query('States').filter(
                (states.domain.in_(whitelist_domains)))

    else:
        query = recorder.query('States').filter(
            (states.domain.in_(SIGNIFICANT_DOMAINS) |
            (states.last_changed == states.last_updated)) &
            ((~states.domain.in_(IGNORE_DOMAINS)) &
            (states.last_updated > start_time)))

    if end_time is not None:
        query = query.filter(states.last_updated < end_time)

    if entity_id is not None:
        query = query.filter_by(entity_id=entity_id.lower())

    states = (
        state for state in recorder.execute(
            query.order_by(states.entity_id, states.last_updated))
        if _is_significant(state))

    return states_to_json(states, start_time, entity_id)


def state_changes_during_period(start_time, end_time=None, entity_id=None):
    """Return states changes during UTC period start_time - end_time."""
    states = recorder.get_model('States')
    query = recorder.query('States').filter(
        (states.last_changed == states.last_updated) &
        (states.last_changed > start_time))

    if end_time is not None:
        query = query.filter(states.last_updated < end_time)

    if entity_id is not None:
        query = query.filter_by(entity_id=entity_id.lower())

    states = recorder.execute(
        query.order_by(states.entity_id, states.last_updated))

    return states_to_json(states, start_time, entity_id)


def get_states(utc_point_in_time, entity_ids=None, run=None):
    """Return the states at a specific point in time."""
    if run is None:
        run = recorder.run_information(utc_point_in_time)

        # History did not run before utc_point_in_time
        if run is None:
            return []

    from sqlalchemy import and_, func

    states = recorder.get_model('States')
    most_recent_state_ids = recorder.query(
        func.max(states.state_id).label('max_state_id')
    ).filter(
        (states.created >= run.start) &
        (states.created < utc_point_in_time)
    )

    if entity_ids is not None:
        most_recent_state_ids = most_recent_state_ids.filter(
            states.entity_id.in_(entity_ids))

    most_recent_state_ids = most_recent_state_ids.group_by(
        states.entity_id).subquery()

    query = recorder.query('States').join(most_recent_state_ids, and_(
        states.state_id == most_recent_state_ids.c.max_state_id))

    return recorder.execute(query)


def states_to_json(states, start_time, entity_id):
    """Convert SQL results into JSON friendly data structure.

    This takes our state list and turns it into a JSON friendly data
    structure {'entity_id': [list of states], 'entity_id2': [list of states]}

    We also need to go back and create a synthetic zero data point for
    each list of states, otherwise our graphs won't start on the Y
    axis correctly.
    """
    result = defaultdict(list)

    entity_ids = [entity_id] if entity_id is not None else None

    # Get the states at the start time
    for state in get_states(start_time, entity_ids):
        state.last_changed = start_time
        state.last_updated = start_time
        result[state.entity_id].append(state)

    # Append all changes to it
    for entity_id, group in groupby(states, lambda state: state.entity_id):
        result[entity_id].extend(group)
    return result


def get_state(utc_point_in_time, entity_id, run=None):
    """Return a state at a specific point in time."""
    states = get_states(utc_point_in_time, (entity_id,), run)

    return states[0] if states else None


# pylint: disable=unused-argument
def setup(hass, config):
    """Setup the history hooks."""
    hass.wsgi.register_view(Last5StatesView(hass, config))
    hass.wsgi.register_view(HistoryPeriodView(hass, config))
    register_built_in_panel(hass, 'history', 'History', 'mdi:poll-box')

    return True


class Last5StatesView(HomeAssistantView):
    """Handle last 5 state view requests."""

    url = '/api/history/entity/<entity:entity_id>/recent_states'
    name = 'api:history:entity-recent-states'

    def __init__(self, hass, config):
         """Initialize the Last5StatesView view."""
         super().__init__(hass)
         self.config = config

    def get(self, request, entity_id):
        """Retrieve last 5 states of entity."""
        return self.json(last_5_states(entity_id))


class HistoryPeriodView(HomeAssistantView):
    """Handle history period requests."""

    url = '/api/history/period'
    name = 'api:history:view-period'
    extra_urls = ['/api/history/period/<datetime:datetime>']

    def __init__(self, hass, config):
         """Initialize the HistoryPeriodView view."""
         super().__init__(hass)
         self.config = config

    def get(self, request, datetime=None):
        """Return history over a period of time."""
        one_day = timedelta(days=1)

        if datetime:
            start_time = dt_util.as_utc(datetime)
        else:
            start_time = dt_util.utcnow() - one_day

        end_time = start_time + one_day
        entity_id = request.args.get('filter_entity_id')

        return self.json(
            get_significant_states(start_time, end_time, entity_id, self.config).values())


def _is_significant(state):
    """Test if state is significant for history charts.

    Will only test for things that are not filtered out in SQL.
    """
    # scripts that are not cancellable will never change state
    return (state.domain != 'script' or
            state.attributes.get(script.ATTR_CAN_CANCEL))
