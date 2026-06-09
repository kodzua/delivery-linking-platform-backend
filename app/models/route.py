from sqlalchemy import Column, Integer, ForeignKey, Enum, DateTime, Numeric, Text, String, Date, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.dialects.postgresql import JSONB
import enum 
from app.database import Base

class route_status_enum(str, enum.Enum) : 
    open = "open"
    full = "full"
    completed = "completed"
    cancelled = "cancelled"

class route_type_enum(str, enum.Enum) :
    one_way = "one_way"
    round_trip = "round_trip"

class wilaya_enum(str, enum.Enum) :
    Adrar = "Adrar"
    Chlef = "Chlef"
    Laghouat = "Laghouat"
    Oum_El_Bouaghi = "Oum El Bouaghi"
    Batna = "Batna"
    Bejaia = "Bejaia"
    Biskra = "Biskra"
    Bechar = "Bechar"
    Blida = "Blida"
    Bouira = "Bouira"
    Tamanrasset = "Tamanrasset"
    Tebessa = "Tebessa"
    Tlemcen = "Tlemcen"
    Tiaret = "Tiaret"
    Tizi_Ouzou = "Tizi Ouzou"
    Algiers = "Algiers"
    Djelfa = "Djelfa"
    Jijel = "Jijel"
    Setif = "Setif"
    Saida = "Saida"
    Skikda = "Skikda"
    Sidi_Bel_Abbes = "Sidi Bel Abbes"
    Annaba = "Annaba"
    Guelma = "Guelma"
    Constantine = "Constantine"
    Medea = "Medea"
    Mostaganem = "Mostaganem"
    Msila = "Msila"
    Mascara = "Mascara"
    Ouargla = "Ouargla"
    Oran = "Oran"
    El_Bayadh = "El Bayadh"
    Illizi = "Illizi"
    Bordj_Bou_Arreridj = "Bordj Bou Arreridj"
    Boumerdes = "Boumerdes"
    El_Tarf = "El Tarf"
    Tindouf = "Tindouf"
    Tissemsilt = "Tissemsilt"
    El_Oued = "El Oued"
    Khenchela = "Khenchela"
    Souk_Ahras = "Souk Ahras"
    Tipaza = "Tipaza"
    Mila = "Mila"
    Ain_Defla = "Ain Defla"
    Naama = "Naama"
    Ain_Temouchent = "Ain Temouchent"
    Ghardaia = "Ghardaia"
    Relizane = "Relizane"
    Timimoun = "Timimoun"
    Bordj_Badji_Mokhtar = "Bordj Badji Mokhtar"
    Ouled_Djellal = "Ouled Djellal"
    Beni_Abbes = "Beni Abbes"
    In_Salah = "In Salah"
    In_Guezzam = "In Guezzam"
    Touggourt = "Touggourt"
    Djanet = "Djanet"
    El_Mghair = "El Mghair"
    El_Meniaa = "El Meniaa"
    Aflou = "Aflou"
    Barika = "Barika"
    Ksar_Chellala = "Ksar Chellala"
    Messaad = "Messaad"
    Ain_Oussera = "Ain Oussera"
    Bou_Saada = "Bou Saada"
    El_Abiodh_Sidi_Cheikh = "El Abiodh Sidi Cheikh"
    El_Kantara = "El Kantara"
    Bir_El_Ater = "Bir El Ater"
    Ksar_El_Boukhari = "Ksar El Boukhari"
    El_Aricha = "El Aricha"

class Route(Base) : 
    __tablename__ = "route"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicle.id"), nullable=False)
    total_capacity = Column(Numeric, nullable=False)
    remaining_capacity = Column(Numeric, nullable=False)
    status = Column(Enum(route_status_enum), nullable=False, default=route_status_enum.open)
    departure_location = Column(Enum(wilaya_enum, values_callable=lambda obj : [e.value for e in obj]), nullable=False)
    arrival_location = Column(Enum(wilaya_enum, values_callable=lambda obj : [e.value for e in obj]), nullable=True)
    departure_date = Column(Date, nullable=False)
    estimated_arrival_date = Column(Date, nullable=True)
    type = Column(Enum(route_type_enum), nullable=False)
    requesting_shippers = Column(MutableList.as_mutable(JSONB), default=[]) # for the shippers requesting to match with a route
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    user = relationship("User", back_populates="route")
    vehicle = relationship("Vehicle", back_populates="route")
    shipment = relationship("Shipment", back_populates="route")
    @property
    def owner(self) :
        return self.user.name if self.user else "unknown"
    @property
    def vehicle_type(self) :
        return self.vehicle.type if self.vehicle else None