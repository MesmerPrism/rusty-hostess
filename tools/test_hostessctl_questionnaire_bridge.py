from __future__ import annotations

import threading
import unittest

from tools.hostessctl import questionnaire_bridge


class HostessCtlQuestionnaireBridgeTests(unittest.TestCase):
    def test_build_open_block_command_uses_maia_spatial_stage(self) -> None:
        payload = questionnaire_bridge.build_open_block_command(
            block="2",
            command_id="cmd-1",
            session_id="session-1",
            participant_ref="P001",
            language_code="de",
        )

        self.assertEqual(payload["protocol_version"], "quest.questionnaire.operator.v1")
        self.assertEqual(payload["action"], "open_questionnaire")
        self.assertEqual(payload["command_name"], "maia_spatial.block2")
        self.assertEqual(
            payload["panel_request"]["open_stage"],
            "maia_spatial:spatial_frame_reference_1",
        )
        self.assertEqual(payload["panel_request"]["questionnaire_state"]["language_code"], "de")

    def test_state_tracks_foreground_after_open_and_dismiss(self) -> None:
        state = questionnaire_bridge.QuestionnaireBridgeState()
        open_payload = questionnaire_bridge.build_open_block_command(
            block="3",
            command_id="cmd-open",
            session_id="session-1",
            participant_ref="P001",
            language_code="en",
        )

        open_response = state.apply_command(open_payload)
        self.assertTrue(open_response["accepted"])
        self.assertTrue(open_response["foreground"]["panel_foreground"])
        self.assertEqual(
            open_response["foreground"]["open_stage"],
            "maia_spatial:spatial_frame_reference_2",
        )

        dismiss_response = state.apply_command(
            questionnaire_bridge.build_dismiss_command(
                command_id="cmd-dismiss",
                session_id="session-1",
            )
        )

        self.assertTrue(dismiss_response["accepted"])
        self.assertFalse(dismiss_response["foreground"]["panel_foreground"])
        self.assertEqual(dismiss_response["last_result"]["status"], "dismissed")

    def test_http_bridge_accepts_status_and_command(self) -> None:
        state = questionnaire_bridge.QuestionnaireBridgeState()
        server = questionnaire_bridge.QuestionnaireBridgeServer(("127.0.0.1", 0), state)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        endpoint = f"http://127.0.0.1:{server.server_address[1]}"

        try:
            status = questionnaire_bridge.get_json(endpoint, questionnaire_bridge.STATUS_PATH)
            self.assertEqual(status["foreground"]["panel_foreground"], False)

            response = questionnaire_bridge.post_json(
                endpoint,
                questionnaire_bridge.COMMAND_PATH,
                questionnaire_bridge.build_open_block_command(
                    block="1",
                    command_id="cmd-http",
                    session_id="session-1",
                    participant_ref="P001",
                    language_code="",
                ),
            )
            self.assertTrue(response["accepted"])
            self.assertTrue(response["foreground"]["panel_foreground"])
            self.assertEqual(
                response["foreground"]["open_stage"],
                "maia_spatial:language_selection",
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2.0)


if __name__ == "__main__":
    unittest.main()

