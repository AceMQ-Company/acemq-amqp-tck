#!/usr/bin/env python3
"""The AceMQ TCK runner and checker.

    python3 runner/tck.py --driver "<command that starts a driver>"
    python3 runner/tck.py --validate      # check the cases against the spec
    python3 runner/tck.py --self-test     # check the matcher

Standard library only, so it runs on any CI image with a python3 on it.

The runner owns everything that is not the library under test: it names the
resources, arranges the broker, plays the misbehaving peer, waits, and decides
whether a case passed. The driver owns only the library calls. A driver cannot
assert anything, which is the point: five libraries asserting their own way is
how the divergences this kit exists for went unnoticed.

See docs/driver-contract.md for the wire protocol and docs/design.md for why.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import queue
import re
import secrets
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VHOST = "%2F"
REQUIREMENT = re.compile(r"\bAMQP-[A-Z]+-\d{3}\b")


class CaseFailed(Exception):
    pass


# --------------------------------------------------------------------------
# matching


def resolve(root, path):
    node = root
    for part in path.split("/"):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def match(actual, pattern, root=None, where="$"):
    """Returns None when ``actual`` satisfies ``pattern``, else why not.

    A dict pattern is a subset match. A dict whose keys all start with ``$`` is
    an operator: $regex, $type, $gt, $gte, $lt, $lte, $sameAs (a /-separated
    path from the root of the thing being matched), $absent, $oneOf, $contains,
    $json (a string that parses as JSON matching the pattern).
    """
    root = actual if root is None else root
    if isinstance(pattern, dict) and pattern and all(k.startswith("$") for k in pattern):
        for op, want in pattern.items():
            problem = operator(op, want, actual, root)
            if problem:
                return f"{where}: {problem}"
        return None
    if isinstance(pattern, dict):
        if not isinstance(actual, dict):
            return f"{where}: expected an object, got {actual!r}"
        for key, want in pattern.items():
            if isinstance(want, dict) and want.get("$absent") is True:
                if key in actual:
                    return f"{where}/{key}: expected absent, got {actual[key]!r}"
                continue
            if key not in actual:
                return f"{where}/{key}: missing (have {sorted(actual)})"
            problem = match(actual[key], want, root, f"{where}/{key}")
            if problem:
                return problem
        return None
    if isinstance(pattern, list):
        if not isinstance(actual, list) or len(actual) != len(pattern):
            return f"{where}: expected {pattern!r}, got {actual!r}"
        for i, (a, p) in enumerate(zip(actual, pattern)):
            problem = match(a, p, root, f"{where}[{i}]")
            if problem:
                return problem
        return None
    if isinstance(pattern, bool) or isinstance(actual, bool):
        return None if actual is pattern else f"{where}: expected {pattern!r}, got {actual!r}"
    return None if actual == pattern else f"{where}: expected {pattern!r}, got {actual!r}"


def operator(op, want, actual, root):
    number = isinstance(actual, (int, float)) and not isinstance(actual, bool)
    if op == "$regex":
        ok = isinstance(actual, str) and re.search(want, actual)
        return None if ok else f"{actual!r} does not match /{want}/"
    if op == "$type":
        types = {"int": number and float(actual).is_integer(), "string": isinstance(actual, str),
                 "object": isinstance(actual, dict), "list": isinstance(actual, list)}
        return None if types.get(want) else f"{actual!r} is not of type {want}"
    if op in ("$gt", "$gte", "$lt", "$lte"):
        if not number:
            return f"{actual!r} is not a number"
        ok = {"$gt": actual > want, "$gte": actual >= want, "$lt": actual < want, "$lte": actual <= want}[op]
        return None if ok else f"{actual!r} is not {op[1:]} {want!r}"
    if op == "$sameAs":
        other = resolve(root, want)
        return None if actual == other and other is not None else f"{actual!r} is not the same as {want} ({other!r})"
    if op == "$oneOf":
        return None if actual in want else f"{actual!r} is not one of {want!r}"
    if op == "$absent":
        return None  # handled by the enclosing object
    if op == "$json":
        # A header whose value is a JSON document (acemq-routing-slip).
        try:
            parsed = json.loads(actual) if isinstance(actual, str) else None
        except ValueError:
            parsed = None
        return match(parsed, want) if parsed is not None else f"{actual!r} is not a JSON string"
    if op == "$contains":
        if not isinstance(actual, list):
            return f"{actual!r} is not a list"
        for wanted in want:
            if all(match(item, wanted, root) for item in actual):
                return f"no element matches {wanted!r}"
        return None
    return f"unknown operator {op}"


def self_test():
    assert match({"a": 1, "b": 2}, {"a": 1}) is None
    assert match({"a": 1}, {"a": 2})
    assert match({"a": 1}, {"b": {"$absent": True}}) is None
    assert match({"a": 1}, {"a": {"$absent": True}})
    assert match("3f2c", {"$regex": "^[0-9a-f]+$"}) is None
    assert match(5, {"$gte": 5, "$lt": 6}) is None
    assert match(6, {"$lt": 6})
    assert match({"p": {"id": "x"}, "h": {"i": "x"}}, {"h": {"i": {"$sameAs": "p/id"}}}) is None
    assert match({"p": {"id": "x"}, "h": {"i": "y"}}, {"h": {"i": {"$sameAs": "p/id"}}})
    assert match(1, {"$type": "int"}) is None and match("1", {"$type": "int"})
    assert match(True, 1) and match(1, True)
    assert match([1, {"a": 2}], [1, {"a": 2}]) is None
    assert match([{"n": "a"}, {"n": "b", "t": 1}], {"$contains": [{"n": "b"}, "x"]})
    assert match([{"n": "a"}, {"n": "b", "t": 1}], {"$contains": [{"n": "b"}, {"n": "a"}]}) is None
    assert match('{"steps": [{"r": "t"}], "done": []}', {"$json": {"steps": [{"r": "t"}]}}) is None
    assert match('{"steps": []}', {"$json": {"steps": [{"r": "t"}]}})
    assert match("not json{", {"$json": {}}) and match(7, {"$json": {}})
    assert substitute({"q": "${ns}.x", "n": ["${ns}"]}, {"ns": "t"}) == {"q": "t.x", "n": ["t"]}
    assert drained([{"body": {"id": "b"}}, {"body": {"id": "a"}}, {"body": {"id": "b"}}, {"body": "raw"}]) == \
        {"count": 4, "ids": ["", "a", "b", "b"]}
    print("self-test: ok")


def substitute(value, names):
    if isinstance(value, str):
        return re.sub(r"\$\{(\w+)\}", lambda m: names.get(m.group(1), m.group(0)), value)
    if isinstance(value, list):
        return [substitute(v, names) for v in value]
    if isinstance(value, dict):
        return {k: substitute(v, names) for k, v in value.items()}
    return value


# --------------------------------------------------------------------------
# the broker, through the management API


class Broker:
    def __init__(self, url):
        parts = urllib.parse.urlsplit(url)
        self.base = f"{parts.scheme}://{parts.hostname}:{parts.port or 15672}"
        token = base64.b64encode(f"{parts.username or 'guest'}:{parts.password or 'guest'}".encode())
        self.auth = "Basic " + token.decode()

    def api(self, method, path, body=None, missing_ok=False):
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(self.base + "/api/" + path, data=data, method=method)
        request.add_header("Authorization", self.auth)
        request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                text = response.read()
                return json.loads(text) if text else None
        except urllib.error.HTTPError as e:
            if missing_ok and e.code == 404:
                return None
            raise CaseFailed(f"management API {method} /api/{path}: {e.code} {e.read()[:300]!r}")

    def wait_ready(self, seconds):
        deadline = time.monotonic() + seconds
        while True:
            try:
                return self.api("GET", "overview")
            except Exception:
                if time.monotonic() > deadline:
                    raise
                time.sleep(1)

    def queue_names(self):
        return {q["name"] for q in self.api("GET", f"queues/{VHOST}?columns=name")}

    def exchange_names(self):
        return {e["name"] for e in self.api("GET", f"exchanges/{VHOST}?columns=name")
                if e["name"] and not e["name"].startswith("amq.")}

    def queue(self, name):
        return self.api("GET", f"queues/{VHOST}/{q(name)}", missing_ok=True)

    def get(self, name):
        """Takes one message off a queue, or returns None."""
        got = self.take(name, 1)
        return got[0] if got else None

    def take(self, name, count):
        """Takes up to ``count`` ready messages off a queue, or returns None if
        there is no such queue. A basic.get inside the broker, so unlike the
        ``messages`` statistic it is exact at the moment it is asked: a message
        a client still holds unacknowledged is not ready and is not returned."""
        got = self.api("POST", f"queues/{VHOST}/{q(name)}/get",
                       {"count": count, "ackmode": "ack_requeue_false", "encoding": "auto", "truncate": 1000000},
                       missing_ok=True)
        return None if got is None else [normalise(m) for m in got]

    def publish(self, exchange, routing_key, body, properties=None):
        payload = body if isinstance(body, str) else json.dumps(body)
        result = self.api("POST", f"exchanges/{VHOST}/{q(exchange or 'amq.default')}/publish", {
            "properties": properties or {}, "routing_key": routing_key,
            "payload": payload, "payload_encoding": "string"})
        return result["routed"]


def q(name):
    return urllib.parse.quote(name, safe="")


def drained(messages):
    """What an ``expect: drain`` matches: how many messages, and their body ids
    sorted, so a duplicate or a missing one shows and arrival order does not."""
    ids = sorted(str(m["body"].get("id")) if isinstance(m["body"], dict) else "" for m in messages)
    return {"count": len(messages), "ids": ids}


def normalise(raw):
    payload = raw["payload"]
    if raw.get("payload_encoding") == "base64":
        payload = base64.b64decode(payload)
        try:
            payload = payload.decode("utf-8")
        except UnicodeDecodeError:
            payload = {"$bytes": raw["payload"]}
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except ValueError:
            pass
    properties = dict(raw.get("properties") or {})
    headers = properties.pop("headers", None) or {}
    return {"body": payload, "headers": headers, "properties": properties,
            "routingKey": raw.get("routing_key"), "exchange": raw.get("exchange"),
            "redelivered": raw.get("redelivered")}


# --------------------------------------------------------------------------
# the driver, over JSON lines on its stdin and stdout


class Driver:
    def __init__(self, command, env):
        self.process = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        env=env, text=True, bufsize=1)
        self.lines = queue.Queue()
        self.next_id = 0
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        for line in self.process.stdout:
            self.lines.put(line)
        self.lines.put(None)

    def call(self, op, args=None, timeout=60.0):
        self.next_id += 1
        ident = self.next_id
        message = dict(args or {}, op=op, id=ident)
        try:
            self.process.stdin.write(json.dumps(message) + "\n")
            self.process.stdin.flush()
        except BrokenPipeError:
            raise CaseFailed(f"driver exited (status {self.process.poll()})")
        deadline = time.monotonic() + timeout
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                raise CaseFailed(f"driver gave no answer to {op} within {timeout:.0f}s")
            try:
                line = self.lines.get(timeout=left)
            except queue.Empty:
                continue
            if line is None:
                raise CaseFailed(f"driver exited (status {self.process.wait()}) during {op}")
            try:
                reply = json.loads(line)
            except ValueError:
                # A library that logs to stdout is not a protocol error; pass it on.
                sys.stderr.write("driver stdout: " + line)
                continue
            if isinstance(reply, dict) and reply.get("id") == ident:
                return reply
            sys.stderr.write("driver stdout (unexpected): " + line)

    def close(self):
        try:
            self.process.stdin.close()
            self.process.wait(timeout=30)
        except Exception:
            self.process.kill()


# --------------------------------------------------------------------------
# a case


class Run:
    def __init__(self, case, broker, driver, verbose):
        self.case = case
        self.broker = broker
        self.driver = driver
        self.verbose = verbose
        self.outcomes = {}
        self.policies = []
        self.threads = []
        self.stop = threading.Event()
        self.peer_errors = []

    def log(self, text):
        if self.verbose:
            print(f"      {text}", flush=True)

    def execute(self):
        queues_before = self.broker.queue_names()
        exchanges_before = self.broker.exchange_names()
        self.queues_before = queues_before
        try:
            begin = self.driver.call("begin", dict(self.case.get("begin", {}), case=self.case["id"], clientName="tck"))
            if not begin.get("ok"):
                raise CaseFailed(f"driver could not begin: {begin.get('error')}")
            for index, step in enumerate(self.case["steps"], 1):
                self.step(index, step)
            if self.peer_errors:
                raise CaseFailed("peer: " + "; ".join(self.peer_errors))
        finally:
            for step in self.case.get("finally", []):
                try:
                    self.step(0, step)
                except CaseFailed as e:
                    print(f"    (finally: {e})")
            self.stop.set()
            try:
                self.driver.call("end", timeout=60)
            except CaseFailed as e:
                print(f"    (end: {e})")
            for thread in self.threads:
                thread.join(timeout=5)
            self.clean_up(queues_before, exchanges_before)

    def clean_up(self, queues_before, exchanges_before):
        """Removes what the case created, and never replaces the case's outcome.

        An exclusive reply queue is still listed for a moment after its owner
        closed, and refuses deletion until the broker has removed it itself, so
        a refusal is retried for a few seconds and then left -- reported, not
        raised, because a raise here would hide whether the case passed and
        stop the rest of the clean-up, leaking into the next case.
        """
        paths = [f"policies/{VHOST}/{q(n)}" for n in self.policies]
        deadline = time.monotonic() + 5
        while True:
            paths += [f"queues/{VHOST}/{q(n)}" for n in self.broker.queue_names() - queues_before]
            paths += [f"exchanges/{VHOST}/{q(n)}" for n in self.broker.exchange_names() - exchanges_before]
            left = []
            for path in dict.fromkeys(paths):
                try:
                    self.broker.api("DELETE", path, missing_ok=True)
                except CaseFailed:
                    left.append(path)
            if not left or time.monotonic() > deadline:
                break
            paths = []
            time.sleep(0.5)
        if left:
            print(f"    (clean-up left {left})", flush=True)

    def step(self, index, step):
        kind = next((k for k in ("driver", "broker", "expect", "sleep") if k in step), None)
        label = f"step {index} ({kind} {step.get(kind)})"
        self.log(label)
        try:
            if kind == "driver":
                self.driver_step(step)
            elif kind == "broker":
                self.broker_step(step)
            elif kind == "expect":
                self.expect(step)
            elif kind == "sleep":
                time.sleep(step["sleep"] / 1000)
            else:
                raise CaseFailed(f"unknown step {step}")
        except CaseFailed as e:
            raise CaseFailed(f"{label}: {e}") from None

    def driver_step(self, step):
        args = {k: v for k, v in step.items() if k not in ("driver", "as", "comment")}
        timeout = args.get("timeoutMs", 0) / 1000 + 60
        started = time.monotonic()
        reply = self.driver.call(step["driver"], args, timeout=timeout)
        outcome = {"ok": bool(reply.get("ok")), "result": reply.get("result") or {},
                   "error": reply.get("error") or {}, "elapsedMs": int((time.monotonic() - started) * 1000)}
        self.log(f"  -> {json.dumps(outcome)[:400]}")
        if "as" in step:
            self.outcomes[step["as"]] = outcome
        elif not outcome["ok"]:
            raise CaseFailed(f"driver error: {outcome['error']}")
        return outcome

    def broker_step(self, step):
        b = self.broker
        op = step["broker"]
        if op == "declareQueue":
            b.api("PUT", f"queues/{VHOST}/{q(step['queue'])}",
                  {"durable": step.get("durable", True), "auto_delete": False, "arguments": step.get("args", {})})
        elif op == "declareExchange":
            b.api("PUT", f"exchanges/{VHOST}/{q(step['exchange'])}",
                  {"type": step.get("type", "direct"), "durable": True, "auto_delete": False, "arguments": {}})
        elif op == "bind":
            b.api("POST", f"bindings/{VHOST}/e/{q(step['exchange'])}/q/{q(step['queue'])}",
                  {"routing_key": step.get("routingKey", ""), "arguments": {}})
        elif op == "policy":
            b.api("PUT", f"policies/{VHOST}/{q(step['name'])}",
                  {"pattern": step["pattern"], "definition": step["definition"],
                   "apply-to": step.get("applyTo", "queues"), "priority": step.get("priority", 100)})
            self.policies.append(step["name"])
        elif op == "clearPolicy":
            b.api("DELETE", f"policies/{VHOST}/{q(step['name'])}", missing_ok=True)
        elif op == "publish":
            routed = b.publish(step.get("exchange", ""), step["routingKey"], step["body"], step.get("properties"))
            if not routed and step.get("mustRoute", True):
                raise CaseFailed("the broker routed the publish nowhere")
        elif op == "closeConnections":
            # Every client connection on the broker: the runner has none of its
            # own, so this is the driver's, cut the way a network failure cuts it.
            closed = 0
            for connection in b.api("GET", "connections?columns=name"):
                b.api("DELETE", f"connections/{q(connection['name'])}", missing_ok=True)
                closed += 1
            if not closed:
                raise CaseFailed("no connections to close")
        elif op == "ctl":
            # rabbitmqctl on the broker under test, for what the management API
            # cannot do (a resource alarm). The action sets ACEMQ_TCK_CTL.
            command = os.environ.get("ACEMQ_TCK_CTL")
            if not command:
                raise CaseFailed("this case needs ACEMQ_TCK_CTL (a command that runs rabbitmqctl on the broker)")
            done = subprocess.run(f"{command} {step['args']}", shell=True, capture_output=True, text=True, timeout=60)
            if done.returncode:
                raise CaseFailed(f"rabbitmqctl {step['args']}: {done.stderr.strip() or done.stdout.strip()}")
        elif op == "respond":
            thread = threading.Thread(target=self.respond, args=(step,), daemon=True)
            thread.start()
            self.threads.append(thread)
        else:
            raise CaseFailed(f"unknown broker step {op}")

    def respond(self, step):
        """Plays a responder: answers each request with exactly the bytes given."""
        answered = 0
        while answered < step.get("count", 1) and not self.stop.is_set():
            try:
                request = self.broker.get(step["queue"])
            except Exception as e:  # noqa: BLE001 -- reported through the case
                self.peer_errors.append(str(e))
                return
            if request is None:
                time.sleep(0.05)
                continue
            props = request["properties"]
            headers = {"x-acemq-correlation": request["headers"].get("x-acemq-correlation", props.get("correlation_id", "")),
                       "x-acemq-causation": request["headers"].get("x-acemq-id", "")}
            headers.update(step.get("headers", {}))
            reply = {"content_type": step.get("contentType", "application/json"), "headers": headers,
                     "delivery_mode": 1, "message_id": secrets.token_hex(16)}
            if props.get("correlation_id"):
                reply["correlation_id"] = props["correlation_id"]
            body = step["body"]
            if body == "$echo":
                body = request["body"]
            if not props.get("reply_to"):
                self.peer_errors.append(f"request had no reply_to: {props}")
                return
            try:
                self.broker.publish("", props["reply_to"], body, reply)
            except Exception as e:  # noqa: BLE001
                self.peer_errors.append(str(e))
                return
            answered += 1

    def expect(self, step):
        within = step.get("withinMs", 0) / 1000
        deadline = time.monotonic() + within
        while True:
            problem = self.check(step)
            if problem is None:
                return
            if time.monotonic() >= deadline:
                raise CaseFailed(problem)
            time.sleep(0.25)

    def check(self, step):
        b = self.broker
        kind = step["expect"]
        if kind == "message":
            message = b.get(step["queue"])
            if message is None:
                return f"no message on {step['queue']}"
            self.log(f"  message: {json.dumps(message)[:600]}")
            problem = match(message, step["match"])
            if problem:
                # Taken off the queue by looking at it, so polling again would
                # report "no message" and hide what was wrong with this one.
                raise CaseFailed(f"{problem}\n        message: {json.dumps(message)[:1500]}")
            return None
        if kind == "drain":
            # Exact where `depth` is a statistic up to a stats interval old, so
            # this is the one to use "immediately after" a driver step. It takes
            # the messages off, so it is checked once and never polled.
            messages = b.take(step["queue"], step.get("max", 1000))
            if messages is None:
                raise CaseFailed(f"queue {step['queue']} does not exist")
            seen = drained(messages)
            self.log(f"  drained: {json.dumps(seen)[:600]}")
            problem = match(seen, step["match"], where=f"drain of {step['queue']}")
            if problem:
                raise CaseFailed(problem)
            return None
        if kind == "depth":
            info = b.queue(step["queue"])
            if info is None:
                return f"queue {step['queue']} does not exist"
            depth = info.get("messages", 0) or 0
            return match(depth, step["count"], where=f"depth of {step['queue']}")
        if kind == "consumers":
            info = b.queue(step["queue"])
            if info is None:
                return f"queue {step['queue']} does not exist"
            return match(info.get("consumers", 0) or 0, step["count"], where=f"consumers on {step['queue']}")
        if kind == "queue":
            info = b.queue(step["queue"])
            if info is None:
                return f"queue {step['queue']} does not exist"
            return match(info, step["match"], where=step["queue"])
        if kind == "queueAbsent":
            return None if b.queue(step["queue"]) is None else f"queue {step['queue']} exists"
        if kind == "noNewQueues":
            new = sorted(n for n in b.queue_names() - self.queues_before if re.search(step["pattern"], n))
            return None if not new else f"queues that should not exist: {new}"
        if kind == "noMessagesIn":
            for name in sorted(b.queue_names()):
                if re.search(step["pattern"], name):
                    info = b.queue(name) or {}
                    if info.get("messages", 0):
                        return f"{name} holds {info['messages']} message(s)"
            return None
        if kind == "step":
            outcome = self.outcomes.get(step["step"])
            if outcome is None:
                return f"no step recorded as {step['step']}"
            return match(outcome, step["match"], where=step["step"])
        if kind == "driver":
            reply = self.driver.call(step["call"]["op"], {k: v for k, v in step["call"].items() if k != "op"})
            if not reply.get("ok"):
                return f"driver error: {reply.get('error')}"
            return match(reply.get("result") or {}, step["match"], where=step["call"]["op"])
        return f"unknown expectation {kind}"


# --------------------------------------------------------------------------
# entry points


def load_cases(selected=None, pending=False):
    """The cases; with ``pending``, also those in cases/pending/ -- cases that
    record a divergence not every library has closed yet, kept out of the
    default run so that the tagged kit is one every library passes."""
    cases = []
    paths = sorted((ROOT / "cases").glob("*.json"))
    if pending:
        paths += sorted((ROOT / "cases" / "pending").glob("*.json"))
    for path in paths:
        case = json.loads(path.read_text())
        case["_file"] = str(path.relative_to(ROOT / "cases"))
        if selected and not any(re.search(s, case["id"]) for s in selected):
            continue
        cases.append(case)
    return cases


def spec_requirements():
    found = {}
    for path in sorted((ROOT / "spec").glob("*.md")):
        for line in path.read_text().splitlines():
            if line.startswith("### "):
                for rid in REQUIREMENT.findall(line):
                    found[rid] = path.name
    return found


def validate():
    """Every case is well formed and names requirements that exist."""
    requirements = spec_requirements()
    problems = []
    ids = set()
    for case in load_cases(pending=True):
        where = case["_file"]
        for key in ("id", "title", "requirements", "steps"):
            if key not in case:
                problems.append(f"{where}: missing {key}")
        if case.get("id") in ids:
            problems.append(f"{where}: duplicate id {case['id']}")
        ids.add(case.get("id"))
        for rid in case.get("requirements", []):
            if rid not in requirements:
                problems.append(f"{where}: {rid} is not a requirement in spec/")
        for step in case.get("steps", []):
            if sum(k in step for k in ("driver", "broker", "expect", "sleep")) != 1:
                problems.append(f"{where}: a step must be exactly one of driver/broker/expect/sleep: {step}")
    covered = {rid for case in load_cases(pending=True) for rid in case.get("requirements", [])}
    print(f"{len(requirements)} requirements, {len(ids)} cases, {len(covered)} requirements covered by a case")
    for problem in problems:
        print("  " + problem)
    return 1 if problems else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--driver", help="shell command that starts the driver")
    parser.add_argument("--amqp", default=os.environ.get("ACEMQ_TCK_AMQP_URL", "amqp://guest:guest@localhost:5672"))
    parser.add_argument("--management", default=os.environ.get("ACEMQ_TCK_MANAGEMENT_URL", "http://guest:guest@localhost:15672"))
    parser.add_argument("--only", action="append", help="regex on case ids; repeatable")
    parser.add_argument("--report", help="write a JSON report here")
    parser.add_argument("--pending", action="store_true", help="also run cases/pending/")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0
    if args.validate:
        return validate()
    if not args.driver:
        parser.error("--driver is required")

    broker = Broker(args.management)
    overview = broker.wait_ready(120)
    version = (ROOT / "VERSION").read_text().strip()
    print(f"AceMQ TCK {version} against RabbitMQ {overview.get('rabbitmq_version')}")

    env = dict(os.environ, ACEMQ_TCK_AMQP_URL=args.amqp)
    driver = Driver(args.driver, env)
    results = []
    try:
        try:
            hello = driver.call("hello", timeout=600)
        except CaseFailed as e:
            print(f"the driver did not start: {e}")
            return 1
        if not hello.get("ok"):
            print(f"driver refused hello: {hello}")
            return 1
        info = hello["result"]
        supported = set(info.get("ops", []))
        print(f"driver: {info.get('library')} {info.get('version')}")
        for case in load_cases(args.only, args.pending):
            names = {"ns": f"tck.{case['id'].lower()}.{secrets.token_hex(3)}"}
            names["nsre"] = re.escape(names["ns"])
            case = substitute(case, names)
            needed = {s["driver"] for s in case["steps"] if "driver" in s}
            needed |= {s["call"]["op"] for s in case["steps"] if s.get("expect") == "driver"}
            started = time.monotonic()
            missing = sorted(needed - supported - {"begin", "end"})
            if missing:
                status, detail = "FAIL", f"driver does not support {missing}"
            else:
                try:
                    Run(case, broker, driver, args.verbose).execute()
                    status, detail = "PASS", ""
                except CaseFailed as e:
                    status, detail = "FAIL", str(e)
            seconds = time.monotonic() - started
            results.append({"id": case["id"], "requirements": case["requirements"], "status": status,
                            "detail": detail, "seconds": round(seconds, 1)})
            print(f"  {status}  {case['id']}  {case['title']}  ({seconds:.1f}s)", flush=True)
            if detail:
                print(f"        {detail}", flush=True)
            if driver.process.poll() is not None:
                print("driver exited; stopping")
                break
    finally:
        driver.close()

    failed = [r for r in results if r["status"] != "PASS"]
    print(f"{len(results) - len(failed)} passed, {len(failed)} failed")
    if args.report:
        Path(args.report).write_text(json.dumps({"tck": version, "driver": info, "results": results}, indent=2))
    return 1 if failed or not results else 0


if __name__ == "__main__":
    sys.exit(main())
