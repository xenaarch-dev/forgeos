"""
ForgeSDK — ForgeOS Agent Development Kit.

Public surface::

    from forge_sdk import ForgeAgent, GBrainLogger

ForgeAgent is the enhanced base class for new pipeline agents.
GBrainLogger provides per-run structured event logging to ~/.forgeos/gbrain/.
"""

from forge_sdk.agent import EventCallback, ForgeAgent
from forge_sdk.glogger import GBrainLogger

__all__ = ["EventCallback", "ForgeAgent", "GBrainLogger"]
