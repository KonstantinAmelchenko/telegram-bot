from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
dp = Dispatcher(storage=MemoryStorage())
from . import commands
from . import profile
from . import events
from . import admin