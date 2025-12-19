import logging
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DEFAULT_OUTPUT_PORTS

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up KVM Select entities from a config entry"""
    _LOGGER.info("🔧 Setting up KVM Select entities from config entry")
    
    # Get the client from the hass data
    client = hass.data[DOMAIN][entry.entry_id]
    
    # Create entities for each output port (1-4)
    entities = []
    for port in range(1, DEFAULT_OUTPUT_PORTS + 1):
        entities.append(KvmSelect(client, port))
    
    # Add entities to Home Assistant
    async_add_entities(entities, True)
    _LOGGER.info(f"✅ Added {len(entities)} KVM Select entities")

class KvmSelect(SelectEntity):
    """KVM Switch Select Entity for Home Assistant"""
    
    def __init__(self, client, output_port):
        """Initialize the KVM Select entity"""
        super().__init__()
        
        # Client and port information
        self.client = client
        self._output_port = output_port
        
        # Entity attributes
        self._attr_name = f"OUT{output_port} Source"
        self._attr_unique_id = f"kvm_select_out{output_port}"
        self._attr_options = ["IN1", "IN2", "IN3", "IN4"]
        self._attr_current_option = None
        self._attr_icon = "mdi:video-input-hdmi"
        
        # State management
        self._initialized = False
        self._update_pending = False
        
        # Register status update callback
        self.client.register_callback(str(output_port), self._handle_status_update)
        
        _LOGGER.info(f"🔧 Created KVM Select entity for Output {output_port}")
    
    async def async_added_to_hass(self):
        """Called when entity is added to Home Assistant"""
        await super().async_added_to_hass()
        _LOGGER.info(f"📥 Entity added to HASS: {self.name}")
        
        # Mark entity as initialized
        self._initialized = True
        
        # Get initial state
        await self.async_update()
    
    async def async_will_remove_from_hass(self):
        """Called when entity is about to be removed from Home Assistant"""
        await super().async_will_remove_from_hass()
        _LOGGER.info(f"📤 Entity will be removed from HASS: {self.name}")
    
    async def async_update(self):
        """Update entity state from KVM switch with protection against overloading"""
        _LOGGER.info(f"🔄 Updating entity: {self.name}")
        
        # Prevent concurrent updates
        if self._update_pending:
            _LOGGER.debug(f"🔒 Update already pending for {self.name}, skipping")
            return
        
        self._update_pending = True
        
        try:
            # Get current status from client with retries handled by client
            current_input = await self.client.get_current_status(self._output_port)
            
            if current_input is not None:
                new_option = f"IN{current_input}"
                
                # Only update if the state has changed
                if self._attr_current_option != new_option:
                    old_option = self._attr_current_option
                    self._attr_current_option = new_option
                    
                    _LOGGER.info(f"📊 State updated for {self.name}: {old_option} → {new_option}")
                    
                    # Write state to Home Assistant if entity is initialized
                    if self._initialized and self.hass:
                        self.async_write_ha_state()
                else:
                    _LOGGER.info(f"📋 State unchanged for {self.name}: {new_option}")
            else:
                _LOGGER.warning(f"⚠️  Failed to get status for {self.name}")
                # If no status available, don't clear existing state - keep last known good state
                if self._attr_current_option is None:
                    _LOGGER.info(f"📋 No previous state for {self.name}, keeping as None")
                else:
                    _LOGGER.info(f"📋 Keeping last known state for {self.name}: {self._attr_current_option}")
        finally:
            # Ensure update pending flag is cleared
            self._update_pending = False
    
    async def async_select_option(self, option: str):
        """Handle option selection from Home Assistant"""
        _LOGGER.info(f"🎯 Selecting option '{option}' for {self.name}")
        
        # Validate option
        if option not in self._attr_options:
            _LOGGER.error(f"❌ Invalid option '{option}' for {self.name}")
            return
        
        try:
            # Extract input source number from option (e.g., "IN2" -> 2)
            input_source = int(option[2:])
            _LOGGER.debug(f"🔢 Parsed input source: {input_source}")
            
            # Set the input source using the client
            success = await self.client.set_input_source(self._output_port, input_source)
            
            if success:
                # Update local state
                old_option = self._attr_current_option
                self._attr_current_option = option
                
                _LOGGER.info(f"✅ Successfully changed {self.name}: {old_option} → {option}")
                
                # Write state to Home Assistant
                if self._initialized and self.hass:
                    self.async_write_ha_state()
            else:
                _LOGGER.error(f"❌ Failed to change {self.name} to {option}")
        except ValueError as e:
            _LOGGER.error(f"❌ Invalid option format '{option}': {e}")
    
    def _handle_status_update(self, device_code: str):
        """Handle status update from KVM client callback"""
        _LOGGER.info(f"📣 Received status update via callback for {self.name}: device_code={device_code}")
        
        try:
            # Convert device code (0-3) to input source (1-4)
            input_code = int(device_code)
            input_source = input_code + 1
            new_option = f"IN{input_source}"
            
            _LOGGER.debug(f"🔢 Translated device_code {device_code} to input_source {input_source} ({new_option})")
            
            # Validate input source (1-4)
            if 1 <= input_source <= 4:
                # Only update if the state has changed
                if self._attr_current_option != new_option:
                    old_option = self._attr_current_option
                    self._attr_current_option = new_option
                    
                    _LOGGER.info(f"📊 Updated state via callback for {self.name}: {old_option} → {new_option}")
                    
                    # Write state to Home Assistant if entity is initialized
                    if self._initialized and self.hass:
                        self.async_write_ha_state()
                else:
                    _LOGGER.debug(f"📋 Callback state unchanged for {self.name}: {new_option}")
            else:
                _LOGGER.warning(f"⚠️  Invalid input source from callback: {input_source} for {self.name}")
        except ValueError as e:
            _LOGGER.error(f"❌ Failed to parse device code '{device_code}' for {self.name}: {e}")
    
    @property
    def available(self):
        """Return if entity is available"""
        return self.client.connected
    
    @property
    def should_poll(self):
        """Return if entity should be polled for updates"""
        return True  # Enable polling to ensure consistent state
    
    @property
    def device_info(self):
        """Return device information for this entity"""
        return {
            "identifiers": {(DOMAIN, "kvm_switch")},
            "name": "KVM Switch",
            "manufacturer": "KVM Manufacturer",
            "model": "KVM Switch",
        }