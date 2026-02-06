"""
Deterministic Electrical Calculator.
Provides zero-hallucination calculations for 70V/100V systems.

CRITICAL: NO LLM FOR ELECTRICAL CALCULATIONS
All calculations are pure Python math for 100% accuracy.
"""

import logging
from dataclasses import dataclass
from typing import Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class CompatibilityResult:
    """Result of a 70V/100V compatibility check."""
    compatible: bool
    total_load: int
    capacity: int
    headroom_percent: float
    message: str


@dataclass
class ImpedanceResult:
    """Result of an impedance calculation."""
    total_impedance: float
    connection: str
    speakers: list[float]
    message: str


class ElectricalCalculator:
    """
    Deterministic electrical calculations for professional audio.
    
    NO LLM USAGE - Pure Python math only.
    
    Handles:
    - 70V/100V transformer compatibility
    - Series/parallel impedance
    - Power summation
    - Wattage tap calculations
    """
    
    # Standard 70V transformer sizes (watts)
    STANDARD_TRANSFORMER_SIZES = [50, 70, 100, 125, 150, 200, 250, 300, 500, 1000]
    
    # Recommended headroom percentages
    MIN_HEADROOM_PERCENT = 10.0  # Minimum safe headroom
    RECOMMENDED_HEADROOM_PERCENT = 20.0  # Recommended operating headroom
    
    @staticmethod
    def calculate_total_power(speakers: list[Union[int, float]]) -> int:
        """
        Calculate total power consumption from speaker wattages.
        
        Args:
            speakers: List of speaker wattages (e.g., [30, 30, 25, 25])
            
        Returns:
            Total watts as integer
            
        Example:
            >>> ElectricalCalculator.calculate_total_power([30, 30, 25, 25])
            110
        """
        if not speakers:
            return 0
        return int(sum(speakers))
    
    @staticmethod
    def verify_70v_compatibility(
        total_watts: int,
        transformer_watts: int,
    ) -> CompatibilityResult:
        """
        Verify if speakers are compatible with a 70V transformer.
        
        Args:
            total_watts: Total speaker load in watts
            transformer_watts: Transformer capacity in watts
            
        Returns:
            CompatibilityResult with compatibility status and headroom
            
        Example:
            >>> result = ElectricalCalculator.verify_70v_compatibility(120, 150)
            >>> result.compatible
            True
            >>> result.headroom_percent
            20.0
        """
        if transformer_watts <= 0:
            return CompatibilityResult(
                compatible=False,
                total_load=total_watts,
                capacity=transformer_watts,
                headroom_percent=0.0,
                message="Invalid transformer capacity",
            )
        
        compatible = total_watts <= transformer_watts
        headroom = ((transformer_watts - total_watts) / transformer_watts) * 100
        
        if not compatible:
            message = (
                f"INCOMPATIBLE: Load ({total_watts}W) exceeds transformer capacity "
                f"({transformer_watts}W) by {total_watts - transformer_watts}W"
            )
        elif headroom < ElectricalCalculator.MIN_HEADROOM_PERCENT:
            message = (
                f"WARNING: Low headroom ({headroom:.1f}%). "
                f"Recommended minimum is {ElectricalCalculator.MIN_HEADROOM_PERCENT}%"
            )
        elif headroom < ElectricalCalculator.RECOMMENDED_HEADROOM_PERCENT:
            message = (
                f"Acceptable: {headroom:.1f}% headroom. "
                f"Recommended is {ElectricalCalculator.RECOMMENDED_HEADROOM_PERCENT}%"
            )
        else:
            message = f"Good: {headroom:.1f}% headroom - optimal configuration"
        
        return CompatibilityResult(
            compatible=compatible,
            total_load=total_watts,
            capacity=transformer_watts,
            headroom_percent=round(headroom, 1),
            message=message,
        )
    
    @staticmethod
    def calculate_impedance(
        speakers: list[float],
        connection: str,
    ) -> ImpedanceResult:
        """
        Calculate total impedance for speakers in series or parallel.
        
        Args:
            speakers: List of speaker impedances in ohms
            connection: 'series' or 'parallel'
            
        Returns:
            ImpedanceResult with total impedance
            
        Example:
            >>> ElectricalCalculator.calculate_impedance([8, 8, 8], 'parallel')
            ImpedanceResult(total_impedance=2.67, connection='parallel', ...)
        """
        if not speakers:
            return ImpedanceResult(
                total_impedance=0.0,
                connection=connection,
                speakers=[],
                message="No speakers provided",
            )
        
        connection = connection.lower()
        
        if connection == 'series':
            total = sum(speakers)
            message = (
                f"Series connection: {' + '.join(str(z) for z in speakers)}Ω = {total:.2f}Ω"
            )
        elif connection == 'parallel':
            # 1/Z_total = 1/Z1 + 1/Z2 + ...
            try:
                total = 1 / sum(1/z for z in speakers if z > 0)
            except ZeroDivisionError:
                return ImpedanceResult(
                    total_impedance=0.0,
                    connection=connection,
                    speakers=speakers,
                    message="Error: Cannot have 0Ω speaker in parallel",
                )
            message = (
                f"Parallel connection: 1/(1/{' + 1/'.join(str(z) for z in speakers)})Ω = {total:.2f}Ω"
            )
        else:
            return ImpedanceResult(
                total_impedance=0.0,
                connection=connection,
                speakers=speakers,
                message=f"Error: Connection must be 'series' or 'parallel', got '{connection}'",
            )
        
        return ImpedanceResult(
            total_impedance=round(total, 2),
            connection=connection,
            speakers=speakers,
            message=message,
        )
    
    @staticmethod
    def recommend_transformer(total_watts: int) -> dict:
        """
        Recommend appropriate transformer size for given load.
        
        Args:
            total_watts: Total speaker load in watts
            
        Returns:
            Dict with recommended and alternative transformer sizes
        """
        recommended = None
        min_required = int(total_watts * 1.2)  # 20% headroom
        
        for size in ElectricalCalculator.STANDARD_TRANSFORMER_SIZES:
            if size >= min_required:
                recommended = size
                break
        
        if recommended is None:
            recommended = ElectricalCalculator.STANDARD_TRANSFORMER_SIZES[-1]
        
        # Find alternatives
        alternatives = [
            s for s in ElectricalCalculator.STANDARD_TRANSFORMER_SIZES
            if s >= total_watts and s != recommended
        ][:2]
        
        headroom = ((recommended - total_watts) / recommended) * 100
        
        return {
            "load_watts": total_watts,
            "recommended_watts": recommended,
            "headroom_percent": round(headroom, 1),
            "alternatives": alternatives,
            "message": f"Recommended: {recommended}W transformer for {total_watts}W load ({headroom:.1f}% headroom)",
        }
    
    @staticmethod
    def calculate_70v_tap(
        desired_spl_reduction: float,
        full_power_watts: int,
    ) -> dict:
        """
        Calculate appropriate wattage tap for desired SPL reduction.
        
        Each -3dB = half power
        
        Args:
            desired_spl_reduction: Desired SPL reduction in dB (positive number)
            full_power_watts: Speaker's full power rating
            
        Returns:
            Dict with recommended tap setting
        """
        if desired_spl_reduction <= 0:
            return {
                "tap_watts": full_power_watts,
                "actual_reduction_db": 0,
                "message": "No reduction needed, use full power tap",
            }
        
        # Power reduction factor: 10^(-dB/10)
        reduction_factor = 10 ** (-desired_spl_reduction / 10)
        target_watts = full_power_watts * reduction_factor
        
        # Standard tap positions (typical for 70V speakers)
        standard_taps = [0.5, 1, 2, 4, 8, 16, 32, 64, 128]
        
        # Find closest standard tap
        closest_tap = min(
            [t for t in standard_taps if t <= full_power_watts],
            key=lambda t: abs(t - target_watts),
            default=standard_taps[0],
        )
        
        # Calculate actual SPL reduction
        if closest_tap > 0 and full_power_watts > 0:
            actual_reduction = 10 * (1 - (closest_tap / full_power_watts))
            actual_reduction = abs(10 * (0 - (closest_tap / full_power_watts)))
            # SPL = 10 * log10(P1/P2)
            import math
            actual_reduction = 10 * math.log10(full_power_watts / closest_tap)
        else:
            actual_reduction = 0
        
        return {
            "target_watts": round(target_watts, 1),
            "tap_watts": closest_tap,
            "actual_reduction_db": round(actual_reduction, 1),
            "message": f"Use {closest_tap}W tap for approximately {actual_reduction:.1f}dB reduction",
        }
    
    @staticmethod
    def max_speakers_for_transformer(
        transformer_watts: int,
        speaker_watts: int,
        headroom_percent: float = 20.0,
    ) -> dict:
        """
        Calculate maximum number of identical speakers for a transformer.
        
        Args:
            transformer_watts: Transformer capacity
            speaker_watts: Wattage per speaker
            headroom_percent: Desired headroom percentage
            
        Returns:
            Dict with max speakers and configuration
        """
        if speaker_watts <= 0:
            return {
                "max_speakers": 0,
                "error": "Speaker wattage must be positive",
            }
        
        usable_watts = transformer_watts * (1 - headroom_percent / 100)
        max_speakers = int(usable_watts / speaker_watts)
        
        actual_load = max_speakers * speaker_watts
        actual_headroom = ((transformer_watts - actual_load) / transformer_watts) * 100
        
        return {
            "max_speakers": max_speakers,
            "speaker_watts": speaker_watts,
            "total_load": actual_load,
            "transformer_watts": transformer_watts,
            "actual_headroom_percent": round(actual_headroom, 1),
            "message": f"Maximum {max_speakers} speakers at {speaker_watts}W each ({actual_load}W total, {actual_headroom:.1f}% headroom)",
        }
    
    @classmethod
    def process_calculation(cls, params: dict) -> dict:
        """
        Process calculation based on extracted parameters.
        
        Args:
            params: Parameters extracted by QueryRouter.extract_calculation_params()
            
        Returns:
            Calculation result dict
        """
        try:
            # 70V compatibility check
            if 'speakers' in params and 'transformer_watts' in params:
                total = cls.calculate_total_power(params['speakers'])
                result = cls.verify_70v_compatibility(total, params['transformer_watts'])
                return {
                    'compatible': result.compatible,
                    'total_load': result.total_load,
                    'capacity': result.capacity,
                    'headroom_percent': result.headroom_percent,
                    'message': result.message,
                    'speakers': params['speakers'],
                }
            
            # Impedance calculation
            if 'impedances' in params and 'connection' in params:
                result = cls.calculate_impedance(
                    params['impedances'],
                    params['connection'],
                )
                return {
                    'total_impedance': result.total_impedance,
                    'connection': result.connection,
                    'speakers': result.speakers,
                    'message': result.message,
                }
            
            # Power summation
            if 'speakers' in params:
                total = cls.calculate_total_power(params['speakers'])
                return {
                    'total_power': total,
                    'speakers': params['speakers'],
                    'message': f"Total power: {total}W",
                }
            
            return {'error': 'Could not determine calculation type from parameters'}
            
        except Exception as e:
            logger.error(f"Calculation error: {e}")
            return {'error': str(e)}
