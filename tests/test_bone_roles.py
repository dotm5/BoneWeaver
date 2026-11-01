import importlib.util
from pathlib import Path
import unittest

# Load the pure module without importing the Blender add-on package.
_spec = importlib.util.spec_from_file_location(
    "bone_roles", Path(__file__).resolve().parents[1] / "boneweaver" / "core" / "bone_roles.py"
)
_roles = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_roles)
bone_role = _roles.bone_role
direction_helper_name = _roles.direction_helper_name
protected_role = _roles.protected_role
secondary_chain_name = _roles.secondary_chain_name


class BoneRoleTests(unittest.TestCase):
    def test_strong_roles_and_precedence(self):
        cases = {
            "root": "ROOT", "Bip001_Root": "ROOT", "IKRoot": "IK",
            "ik_hand_gun": "IK", "hand_r_ik": "IK", "weapon_r": "WEAPON_ATTACHMENT",
            "Bip001_Prop1": "WEAPON_ATTACHMENT", "gun": "WEAPON_ATTACHMENT",
            "muzzle_end": "WEAPON_ATTACHMENT", "camera": "CONTROL",
            "aim_target": "CONTROL", "magazine_tip": "WEAPON_ATTACHMENT", "WeaponSocket": "SOCKET",
            "VB root hand": "VIRTUAL", "hand_ctrl": "CONTROL",
            "hand_effector": "CONTROL", "hand_effector_tip": "CONTROL",
            "Root_Motion": "UNKNOWN", "skin": "UNKNOWN", "index": "PRIMARY_JOINT",
            "pelvis": "PRIMARY_JOINT", "spine_03": "PRIMARY_JOINT",
            "upperarm_l": "PRIMARY_JOINT", "L_Index_F03": "PRIMARY_JOINT",
            "L_Index_F04": "PRIMARY_JOINT", "mystery": "UNKNOWN",
        }
        for name, expected in cases.items():
            with self.subTest(name=name):
                self.assertEqual(bone_role(name), expected)
        self.assertEqual(bone_role("ik_hand", is_socket=True), "SOCKET")
        self.assertEqual(bone_role("", is_socket=True), "SOCKET")
        self.assertEqual(bone_role("Character:hand_r_ik"), "IK")

    def test_direction_markers_are_terminal_and_effector_is_control(self):
        for name in ("hand_end", "HeadTip", "finger_nub_01", "tip"):
            with self.subTest(name=name):
                self.assertTrue(direction_helper_name(name, "hand"))
                self.assertEqual(bone_role(name), "DIRECTION_HELPER")
        for name in ("effector", "hand_effector_tip", "tip_joint", "weekend", ""):
            with self.subTest(name=name):
                self.assertFalse(direction_helper_name(name, "hand"))

    def test_secondary_names_require_separate_safety_checks(self):
        for name in ("hair_01", "skirt_l_02", "cloth", "tail_03", "breast_l",
                     "physics_body", "MassCenter", "mass_center", "upperarm_twist_01",
                     "SR_upperarm_l", "ST_thigh_r"):
            with self.subTest(name=name):
                self.assertTrue(secondary_chain_name(name))
                self.assertEqual(bone_role(name), "SECONDARY")
                self.assertFalse(protected_role(bone_role(name)))
        self.assertFalse(secondary_chain_name("chair"))
        self.assertEqual(bone_role("hair_root"), "SECONDARY")

    def test_protection_is_explicit(self):
        for role in ("ROOT", "IK", "SOCKET", "WEAPON_ATTACHMENT", "CONTROL",
                     "VIRTUAL", "PRIMARY_JOINT"):
            self.assertTrue(protected_role(role), role)
        for role in ("SECONDARY", "DIRECTION_HELPER", "UNKNOWN", "something_else"):
            self.assertFalse(protected_role(role), role)

    def test_audited_game_utility_names(self):
        for name in ("MarkCase", "HitCase", "WingCase", "MiddleCase", "mark_case_01",
                     "HuluProp01", *(f"WeaponProp{i:02}" for i in range(1, 8))):
            with self.subTest(name=name):
                role = bone_role(name)
                self.assertEqual(role, "WEAPON_ATTACHMENT")
                self.assertTrue(protected_role(role))
        for name in ("CameraPosition", "NekoBotHit"):
            self.assertEqual(bone_role(name), "CONTROL")
            self.assertTrue(protected_role(bone_role(name)))
        for name in ("SocketADS", "LHS_Socket"):
            self.assertEqual(bone_role(name), "SOCKET")
            self.assertTrue(protected_role(bone_role(name)))
        for name in ("ik_foot_root", "ik_hand_gun", "ik_hand_l"):
            self.assertEqual(bone_role(name), "IK")
        for name in ("showcase", "briefcase", "casework"):
            self.assertEqual(bone_role(name), "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
